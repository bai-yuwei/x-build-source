import os
import subprocess
import chardet
import docker
import shutil
from docker.errors import ImageNotFound, ContainerError, APIError
from typing import Dict, Any, Optional, Union

class DockerBuilder:
    def __init__(self, project, dockerfile, dockerImage, context, dockerBuildCmd, resultDir, host_output_dir=None, container_name=None):
        self.project = project
        self.dockerfile = dockerfile
        self.dockerImage = dockerImage
        self.context = context
        if dockerBuildCmd is None:
            self.dockerBuildCmd = f"./build.exe {project}"
        else:
            self.dockerBuildCmd = dockerBuildCmd
        self.resultDir = os.path.join(os.getcwd(), context, resultDir)
        self.host_output_dir = host_output_dir or os.path.join(os.getcwd(), "build", project)
        self.container_name = container_name or f"{project}_{dockerImage.replace(':', '_')}"
        self.client = None
        self.container = None

    def _init_docker_client(self):
        """初始化Docker客户端，增加重试机制"""
        try:
            if self.client is None:
                self.client = docker.from_env()
                self.client.ping()
                print("Docker客户端初始化成功")
            return True
        except Exception as e:
            print(f"Docker客户端初始化失败: {e}")
            return False

    def _get_container(self):
        """检查容器是否存在并返回容器对象"""
        try:
            return self.client.containers.get(self.container_name)
        except docker.errors.NotFound:
            return None
        except APIError as e:
            print(f"检查容器时API错误: {e}")
            return None
    def _copy_artifacts_direct_mount(self):
        """
        简化版本 - 适用于直接挂载映射的情况
        """
        try:
            # 假设 host_output_dir 就是直接挂载的路径
            source_path = self.resultDir
            target_path = self.host_output_dir  # 你希望复制到的最终位置

            print(f"从挂载目录复制: {source_path} -> {target_path}")

            if not os.path.exists(source_path):
                print(f"❌ 挂载目录不存在: {source_path}")
                return False

            # 确保目标目录存在
            os.makedirs(target_path, exist_ok=True)

            # 复制所有内容
            for item in os.listdir(source_path):
                source_item = os.path.join(source_path, item)
                target_item = os.path.join(target_path, item)

                if os.path.isdir(source_item):
                    if os.path.exists(target_item):
                        shutil.rmtree(target_item)
                    shutil.copytree(source_item, target_item)
                else:
                    shutil.copy2(source_item, target_item)

            print(f"✅ 成果物复制完成: {target_path}")
            return True

        except Exception as e:
            print(f"❌ 复制失败: {e}")
            return False

    def _start_container_with_realtime_output(self, container):
        """启动容器并实时显示输出[1,2](@ref)"""
        try:
            print("启动容器...")
            container.start()
            
            # # 实时获取容器输出[2](@ref)
            # print("开始实时输出容器日志:")
            # try:
            #     # 使用流式日志输出[2](@ref)
            #     logs_stream = container.logs(
            #         stream=True, 
            #         follow=True, 
            #         stdout=True, 
            #         stderr=True,
            #         timestamps=True
            #     )
                
            #     # 实时打印日志输出
            #     for line in logs_stream:
            #         # 解码并清理输出
            #         line_decoded = line.decode('utf-8').strip()
            #         if line_decoded:
            #             print(f"[容器日志] {line_decoded}")
                        
            # except Exception as log_error:
            #     print(f"日志流读取错误: {log_error}")
            #     # 如果流式读取失败，尝试一次性获取日志
            #     try:
            #         logs = container.logs(stdout=True, stderr=True, timestamps=True)
            #         print("容器完整日志:")
            #         print(logs.decode('utf-8'))
            #     except Exception as e:
            #         print(f"获取完整日志失败: {e}")
            
            # 检查容器状态
            container.reload()
            exit_code = container.attrs['State']['ExitCode']
            
            if exit_code == 0:
                print("✅ 容器执行成功完成!")
                return True
            else:
                print(f"❌ 容器异常退出，退出码: {exit_code}")
                return False
                
        except Exception as e:
            print(f"容器启动失败: {e}")
            return False

    def _execute_command_with_realtime_output(self, container, command):
        """通过subprocess执行Docker命令（更稳定的替代方案）"""
        try:
        # 构建容器命令
            docker_cmd = [
                'docker', 'run', '--rm',
                '-v', f'{os.path.abspath(self.context)}:/workspace',
                '-w', '/workspace',
                '--entrypoint', '',
                self.dockerImage,
                'sh', '-c', """
                    ./build.sh
                    BUILD_EXIT_CODE=$?
                    echo "build success, exit code: $BUILD_EXIT_CODE"
                    exit $BUILD_EXIT_CODE
                """
            ]

            print(f"执行一次性构建命令: {' '.join(docker_cmd)}")

            process = subprocess.Popen(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                bufsize=1
            )


            # 实时读取输出
            print("命令输出:")
            # 直接迭代输出行，更Pythonic的方式
            for raw_output in iter(process.stdout.readline, ''):
                output_decoded = raw_output.strip()
                if output_decoded:
                    print(f"[输出] {output_decoded}")

            exit_code = process.wait()

            if exit_code == 0:
                print("✅ 一次性构建成功完成，容器已自动退出")
                return True
            else:
                print(f"❌ 构建失败，退出码: {exit_code}")
                return False

        except Exception as e:
            print(f"子进程执行错误: {e}")
            return False

    def _copy_files_to_container(self, container):
        """复制文件到容器并显示进度"""
        try:
            print("复制文件到容器...")
            host_path = os.path.abspath(self.context)
            container_path = "/workspace"
            
            # 检查源路径是否存在
            if not os.path.exists(host_path):
                print(f"错误：源路径不存在: {host_path}")
                return False
            
            # 使用docker cp命令复制文件[6](@ref)
            docker_cp_cmd = [
                "docker", "cp", 
                host_path, 
                f"{container.id}:{container_path}"
            ]
            
            # 执行复制命令并显示输出
            result = subprocess.run(
                docker_cp_cmd, 
                capture_output=True, 
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                print("✅ 文件复制成功")
                # 显示复制详情
                if result.stdout:
                    print(f"复制输出: {result.stdout}")
                return True
            else:
                print(f"❌ 文件复制失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ 文件复制超时")
            return False
        except Exception as e:
            print(f"❌ 文件复制错误: {e}")
            return False

    def _build_image_with_realtime_output(self, dockerfile_path):
        """构建镜像并实时显示构建输出（完整版）"""
        try:
            print("尝试通过命令行构建镜像进行调试...")

            # 计算路径（使用相同的逻辑）
            if os.path.isdir(dockerfile_path):
                dockerfile_dir = dockerfile_path
                dockerfile_full_path = os.path.join(dockerfile_path, "Dockerfile")
            else:
                dockerfile_dir = os.path.dirname(dockerfile_path)
                dockerfile_full_path = dockerfile_path

            build_context = os.path.abspath(os.path.join(dockerfile_dir, "../.."))
            dockerfile_relative_path = os.path.relpath(dockerfile_full_path, build_context)

            # 构建命令行
            cmd = [
                'docker', 'build',
                '-t', self.dockerImage,
                '-f', dockerfile_full_path,
                build_context
            ]

            print(f"执行命令行: {' '.join(cmd)}")
            print(f"工作目录: {os.getcwd()}")

            # 执行命令并实时输出
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                bufsize=1,
                universal_newlines=True
            )

            # 实时读取输出
            print("命令行构建输出:")
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.strip())

            return_code = process.wait()

            if return_code == 0:
                print("✅ 命令行构建成功")
                return True
            else:
                print(f"❌ 命令行构建失败，退出码: {return_code}")
                return False

        except Exception as e:
            print(f"命令行构建错误: {e}")
            return False

    def _start_container(self, container):
        """启动容器并执行构建流程"""
        try:
            # 1. 复制文件到容器
            # if not self._copy_files_to_container(container):
            #     return False
            # 2. 启动容器
            if not self._start_container_with_realtime_output(container):
                return False
            # 3. 执行构建命令（如果有）
            if self.dockerBuildCmd:
                print("开始执行构建命令...")
                code_dir_name = os.path.basename(os.path.normpath(self.context))
                code_path_in_container = f"/workspace/{code_dir_name}"
                print(f"代码在容器内的路径: {code_path_in_container}")
                if isinstance(self.dockerBuildCmd, str):
                    # 字符串命令：添加cd命令
                    modified_build_cmd = f"cd {code_path_in_container} && {self.dockerBuildCmd}"
                else:
                    # 列表命令：需要在适当位置插入cd命令
                    modified_build_cmd = ["cd", code_path_in_container, "&&"] + self.dockerBuildCmd

                print(f"修改后的构建命令: {modified_build_cmd}")
                if not self._execute_command_with_realtime_output(container, modified_build_cmd):
                    return False
            else:
                print("⚠️ 没有构建命令，直接启动容器")
                # 如果没有构建命令，直接启动并监控容器输出
                if not self._start_container_with_realtime_output(container):
                    return False
            
            if True:
                print("构建完成，开始复制成果物...")
                copy_success = self._copy_artifacts_direct_mount()
                
                # 复制成果物是构建流程的重要部分，但不应影响构建本身的成功状态
                if not copy_success:
                    print("⚠️ 构建成功但复制成果物失败")
                    # 根据需求决定是否将复制失败视为整体失败
                    # 这里我们继续返回构建成功，但记录复制问题
                else:
                    print("✅ 构建和成果物复制均完成")
            else:
                print("❌ 构建失败，跳过成果物复制")
            return True
            
        except Exception as e:
            print(f"❌ 容器操作失败: {e}")
            return False

    def _get_container_config(self):
        """获取容器配置"""
        config = {
            'image': self.dockerImage,
            'environment': {'DOCKER_PROJECT': self.project},
            'working_dir': '/workspace',
            'stdin_open': True,  # 保持标准输入打开[1](@ref)
            'tty': True,         # 分配伪终端[1](@ref)
            'auto_remove': False,
            'detach': True
        }
        
        # 如果没有构建命令，设置默认命令保持容器运行
        if not self.dockerBuildCmd:
            config['command'] = ['tail', '-f', '/dev/null']  # 保持容器运行
        
        return config

    # 其他方法保持不变（build_project, _build_on_host, _build_in_docker, cleanup等）
    # 只需将原来的方法实现复制到这里，保持原样即可

    def build_project(self):
        """构建项目的主要逻辑"""
        original_cwd = os.getcwd()
        
        if os.environ.get('DOCKER_PROJECT'):
            return self._build_on_host(original_cwd)
        else:
            return self._build_in_docker()

    def _build_on_host(self, original_cwd):
        """在宿主机上执行构建"""
        print(f"在宿主机上构建项目: {self.project}")
        try:
            if not os.path.exists(self.context):
                print(f"错误：上下文目录不存在: {self.context}")
                return False
                
            os.chdir(self.context)
            print(f"切换到目录: {os.getcwd()}")
            
            if not self.dockerBuildCmd:
                self.dockerBuildCmd = f"./build.exe {self.project}"
            
            print(f"执行构建命令: {self.dockerBuildCmd}")
            print("开始实时输出:")
            
            # 使用subprocess.Popen实现实时输出
            if isinstance(self.dockerBuildCmd, str):
                process = subprocess.Popen(
                    self.dockerBuildCmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
            else:
                process = subprocess.Popen(
                    self.dockerBuildCmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
            
            # 实时读取输出
            with process:
                for line in process.stdout:
                    print(f"[构建输出] {line.strip()}")
                
                process.wait()
                return_code = process.returncode
            
            if return_code == 0:
                print("✅ 宿主机构建成功完成!")
                return True
            else:
                print(f"❌ 宿主机构建失败，退出码: {return_code}")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"❌ 构建命令执行失败: {e}")
            return False
        except Exception as e:
            print(f"❌ 执行过程中发生错误: {e}")
            return False
        finally:
            os.chdir(original_cwd)

    def _build_in_docker(self):
        """在Docker环境中构建项目"""
        print(f"在Docker环境中构建项目: {self.project}")
        
        if not self._init_docker_client():
            return False
        
        try:
            # 检查构建上下文
            if not os.path.exists(self.context):
                print(f"错误：构建上下文目录不存在: {self.context}")
                return False
            
            dockerfile_path = os.path.join(os.getcwd(), 'docker', self.dockerfile)
            container_config = self._get_container_config()
            
            # 检查镜像是否存在
            image_exists = False
            try:
                self.client.images.get(self.dockerImage)
                image_exists = True
                print(f"镜像已存在: {self.dockerImage}")
            except ImageNotFound:
                print(f"镜像不存在，需要构建: {self.dockerImage}")
                image_exists = False
            
            # 构建镜像（如果不存在）
            if not image_exists:
                image = self._build_image_with_realtime_output(dockerfile_path)
                if not image:
                    return False
            else:
                image = self.client.images.get(self.dockerImage)
            
            # 创建或获取容器
            container = self._get_container()
            if container:
                print(f"使用现有容器: {self.container_name}")
                # 可以添加配置检查逻辑
            else:
                print("创建新容器...")
                container = self._create_container(container_config)
            
            # 启动容器并执行构建
            success = self._start_container(container)
            
            # 清理资源
            if container:
                print("清理容器...")
                # try:
                #     container.remove(force=True)
                # except Exception as e:
                #     print(f"清理容器时出错: {e}")
            
            return success
            
        except Exception as e:
            print(f"❌ Docker构建过程失败: {e}")
            # 确保清理资源
            if hasattr(self, 'container') and self.container:
                try:
                    self.container.remove(force=True)
                except:
                    pass
            return False

    def cleanup(self):
        """清理资源"""
        try:
            if self.container:
                self.container.remove(force=True)
            if self.client:
                self.client.close()
            print("资源清理完成")
        except Exception as e:
            print(f"清理资源时出错: {e}")

    def _create_container(self, container_config):
        """创建新容器"""
        try:
            print(f"创建新容器: {self.container_name}")
            
            # 检查是否已存在同名容器
            existing_container = self._get_container()
            if existing_container:
                print(f"发现已存在的容器 {self.container_name}，正在删除...")
                existing_container.remove(force=True)
            
            # 创建容器
            container = self.client.containers.create(
                **container_config,
                name=self.container_name
            )
            print(f"容器创建成功: {container.id}")
            return container
            
        except ContainerError as e:
            print(f"容器创建失败: {e}")
            raise
        except APIError as e:
            print(f"Docker API错误: {e}")
            raise
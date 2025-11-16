import sys
import os
import subprocess
from common.common import ConfigManager
from pathlib import Path

class CMakeBuilder:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
    def build(self):
        projects = self.config_manager.get_all_config_names()
        for project in projects:
            platform = self.config_manager.get_platform(project)
            print(f"platform: {platform}")
            compiler = self.config_manager.get_compiler(project)
            print(f"compiler: {compiler}")
            buildType = self.config_manager.get_type(project)
            print(f"type: {buildType}")
            cflags = self.config_manager.get_cflags(project)
            print(f"cflags: {cflags}")
            lflags = self.config_manager.get_lflags(project)
            print(f"lflags: {lflags}")
            print(f"Building {project} for platform {platform}")
            self.build_project(project, platform, compiler, buildType, cflags, lflags)

    def build_project(self, project, platform, compiler, buildType, cflags, lflags):
        """使用新式 CMake 命令构建项目"""

        # 确保构建目录存在
        base_path = os.path.dirname(sys.executable)
        build_dir = f"build/{project}"
        os.makedirs(build_dir, exist_ok=True)

        try:
            # 配置项目（使用 -S 和 -B 参数）
            print("配置 CMake 项目...")
            toolchain_file = Path(f"{base_path}/config/{platform}/{platform}-{compiler}.cmake")
            print(f"toolchain_file: {toolchain_file}")
            if not toolchain_file.exists():
                print(f"错误: 找不到工具链文件: {toolchain_file}")
                return False
            subprocess.run([
                "cmake", 
                "-S", f"{base_path}/code/{project}",
                "-B", build_dir,
                "-G", "Ninja",
                f"-DCMAKE_TOOLCHAIN_FILE={base_path}/config/{platform}/{platform}-{compiler}.cmake",
                f"-DCMAKE_BUILD_TYPE={buildType}",
                # 将cflags列表合并成一个字符串，用空格分隔
                f"-DCMAKE_CXX_FLAGS={' '.join(cflags)}" if cflags else "",
                # 将lflags列表合并成一个字符串，用空格分隔
                f"-DCMAKE_EXE_LINKER_FLAGS={' '.join(lflags)}" if lflags else "",
            ], check=True)

            # 构建项目
            print("构建项目...")
            subprocess.run([
                "cmake",
                "--build", build_dir,
                "--parallel", str(os.cpu_count())
            ], check=True)

            print("install项目...")
            subprocess.run([
                "cmake",
                "--install", build_dir
            ], check=True)

            print("构建成功!")
            return True

        except subprocess.CalledProcessError as e:
            print(f"构建失败: {e}")
            return False
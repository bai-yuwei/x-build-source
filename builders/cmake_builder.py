import sys
import os
import subprocess
from pathlib import Path

class CMakeBuilder:
    def __init__(self, project, platform, compiler, buildType, cflags, lflags):
        self.project = project
        self.platform = platform
        self.compiler = compiler
        self.buildType = buildType
        self.cflags = cflags
        self.lflags = lflags

    def build_project(self):
        """使用新式 CMake 命令构建项目"""

        # 确保构建目录存在
        basePath = os.path.dirname(sys.executable)
        buildDir = f"build/{self.project}"
        os.makedirs(buildDir, exist_ok=True)

        try:
            # 配置项目（使用 -S 和 -B 参数）
            print("配置 CMake 项目...")
            toolchainFile = Path(f"{basePath}/config/{self.platform}/{self.platform}-{self.compiler}.cmake")
            print(f"toolchainFile: {toolchainFile}")
            if not toolchainFile.exists():
                print(f"错误: 找不到工具链文件: {toolchainFile}")
                return False
            subprocess.run([
                "cmake", 
                "-S", f"{basePath}/code/{self.project}",
                "-B", buildDir,
                "-G", "Ninja",
                f"-DCMAKE_TOOLCHAIN_FILE={basePath}/config/{self.platform}/{self.platform}-{self.compiler}.cmake",
                f"-DCMAKE_BUILD_TYPE={self.buildType}",
                # 将cflags列表合并成一个字符串，用空格分隔
                f"-DCMAKE_CXX_FLAGS={' '.join(self.cflags)}" if self.cflags else "",
                # 将lflags列表合并成一个字符串，用空格分隔
                f"-DCMAKE_EXE_LINKER_FLAGS={' '.join(self.lflags)}" if self.lflags else "",
            ], check=True)

            # 构建项目
            print("构建项目...")
            subprocess.run([
                "cmake",
                "--build", buildDir,
                "--parallel", str(os.cpu_count())
            ], check=True)

            print("install项目...")
            subprocess.run([
                "cmake",
                "--install", buildDir
            ], check=True)

            print("构建成功!")
            return True

        except subprocess.CalledProcessError as e:
            print(f"构建失败: {e}")
            return False
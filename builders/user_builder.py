import sys
import os
import subprocess

class UserBuilder:
    def __init__(self, project, userBuildCmd):
        self.project = project
        self.userBuildCmd = userBuildCmd


    def build_project(self):
        """使用自定义构建命令构建项目"""
        print(f"自定义构建命令: {self.userBuildCmd}")
        basePath = os.path.dirname(sys.executable)
        codeDir = f"code/{self.project}"
        codeDir = os.path.join(basePath, codeDir)

        # 检查目录是否存在
        if os.path.exists(codeDir) and os.path.isdir(codeDir):
            os.chdir(codeDir)
            print(f"已切换到项目目录: {os.getcwd()}")
        else:
            print(f"错误：项目目录不存在 {codeDir}")
            # 这里应该进行错误处理，例如return False或抛出异常
        subprocess.run(self.userBuildCmd, check=True)
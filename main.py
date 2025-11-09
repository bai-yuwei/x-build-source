import os
import sys
import shutil
from typing import List, Dict, Optional, Callable
from pathlib import Path
from common.common import ConfigManager
from builders.cmake_builder import CMakeBuilder


def clean_build_directory(clear_dir):
    """使用纯 Python 清理构建目录（完全跨平台）"""

    clear_dir = Path(clear_dir)
    if not clear_dir.exists():
        print(f"No build directory to clean: {clear_dir}")
        return True
    
    print(f"Cleaning build directory: {clear_dir}")
    
    # 递归删除目录及其内容
    try:
        for item in clear_dir.iterdir():
            if item.is_file():
                item.unlink()  # 删除文件
            elif item.is_dir():
                shutil.rmtree(item)  # 删除子目录
        
        # 如果目录为空，尝试删除它
        if not any(clear_dir.iterdir()):
            clear_dir.rmdir()
            
        print(f"Successfully cleaned build directory: {clear_dir}")
        return True
    except Exception as e:
        print(f"Error cleaning build directory: {e}")
        return False

def handle_help():
    print("Usage: build.exe [clean <project_name> | clean]")

def handle_dclean(config_manager: ConfigManager, args: List[str]):
    clear_dir = f"build"
    if os.path.exists(clear_dir):
        print(f"Cleaning build directory: {clear_dir}")
        clean_build_directory(clear_dir)
    else:
        print(f"No build directory to clean: {clear_dir}")

def handle_clean(config_manager: ConfigManager, args: List[str]):
    if not args:
        args = config_manager.get_all_config_names()
    for arg in args:
        clear_dir = f"build/{arg}"
        if os.path.exists(clear_dir):
            print(f"Cleaning build directory: {clear_dir}")
            clean_build_directory(clear_dir)
        else:
            print(f"No build directory to clean: {clear_dir}")

def handle_build(config_manager: ConfigManager, args: List[str]):
    cmake_builder = CMakeBuilder(config_manager)
    cmake_builder.build()

def handle_list(config_manager: ConfigManager, args: List[str]):
    """列出所有可用的项目配置"""
    projects = config_manager.get_all_config_names()
    print("Available projects:")
    for project in projects:
        print(f"  - {project}")

# 创建命令映射字典
COMMAND_HANDLERS: Dict[str, Callable] = {
    "dclean": handle_dclean,
    "clean": handle_clean,
    "list": handle_list,
    "help": lambda cm, args: handle_help(),
    "--help": lambda cm, args: handle_help(),
    "-h": lambda cm, args: handle_help(),
}

def main():
    config_manager = ConfigManager()
    if len(sys.argv) == 1:
        handle_build(config_manager, config_manager.get_all_config_names())
        return
    command = sys.argv[1]
    args = sys.argv[2:] 
    handler = COMMAND_HANDLERS.get(command)
    if handler:
        try:
            handler(config_manager, args)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        print(f"Unknown command: {command}")
        handle_help()
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
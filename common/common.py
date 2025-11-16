
import json
from typing import Dict, List, Optional


class ConfigManager:
    def __init__(self):
        self.data = None
        self.file = "buildConfig.json"
        self.load()
    
    def load(self):
        try:
            with open(self.file, "r") as f:
                self.data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件未找到: {self.file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析错误: {e}")
        
    @property
    def get_version(self) -> int:
        return self.data.get("version", 0)
    
    def get_all_configs(self) -> List[Dict]:
        """获取所有配置项"""
        return self.data.get('config', [])
    
    def get_all_config_names(self) -> List[str]:
        if not isinstance(self.data, dict):
            return []
        configs = self.data.get('config')
        if not isinstance(configs, list):
            return []
        names = []
        for config in configs:
            if not isinstance(config, dict):
                continue
            name = config.get('name')
            if isinstance(name, str) and name.strip():
                names.append(name)
        return names

    def get_config(self, name: str) -> Optional[Dict]:
        """根据名称获取特定配置项"""
        for config in self.data.get('config', []):
            if config.get('name') == name:
                return config
        return None
    
    def get_platform(self, name: str) -> str:
        config = self.get_config(name)
        if config:
            return config.get('platform', "winArm")
        return "winArm"
    
    def get_compiler(self, name: str) -> str:
        config = self.get_config(name)
        if config:
            return config.get('compiler', "gcc")
        return "gcc"
    def get_type(self, name: str) -> str:
        config = self.get_config(name)
        if config:
            return config.get('type', "debug")
        return "debug"
    
    def get_cflags(self, name: str) -> List[str]:
        config = self.get_config(name)
        if config:
            return config.get('cflags', [])
        return []
    
    def get_lflags(self, name: str) -> List[str]:
        config = self.get_config(name)
        if config:
            return config.get('lflags', [])
        return []
    
    def get_userBuildCmd(self, name: str) -> List[str]:
        config = self.get_config(name)
        if config:
            return config.get('userBuildCmd', [])
        return []
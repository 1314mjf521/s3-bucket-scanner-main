"""插件加载器模块"""
import importlib
import os
import sys
from typing import Type, Optional, Dict, Any
from abc import ABC


class PluginLoader:
    """插件加载器"""
    
    def __init__(self, base_dir: str = '.'):
        self.base_dir = base_dir
        self.loaded_plugins: Dict[str, Any] = {}
    
    def load_plugin(self, module_path: str, class_name: str) -> Optional[Any]:
        """动态加载插件类
        
        Args:
            module_path: 模块路径，如 'exporter.excel_exporter'
            class_name: 类名，如 'ExcelExporterImpl'
            
        Returns:
            插件类实例，失败返回 None
        """
        try:
            # 导入模块
            module = importlib.import_module(module_path)
            
            # 获取类
            plugin_class = getattr(module, class_name)
            
            # 创建实例
            instance = plugin_class()
            
            # 缓存实例
            self.loaded_plugins[f"{module_path}.{class_name}"] = instance
            
            return instance
            
        except ImportError as e:
            print(f"Failed to import module {module_path}: {e}")
            return None
        except AttributeError as e:
            print(f"Class {class_name} not found in module {module_path}: {e}")
            return None
        except Exception as e:
            print(f"Failed to load plugin {module_path}.{class_name}: {e}")
            return None
    
    def load_exporter(self, exporter_type: str, config: Any) -> Optional[Any]:
        """根据类型加载导出器
        
        Args:
            exporter_type: 导出器类型，如 'excel' 或 'database'
            config: 配置对象
            
        Returns:
            导出器实例，失败返回 None
        """
        exporter_map = {
            'excel': ('exporter.excel_exporter', 'ExcelExporterImpl'),
            'csv': ('exporter.csv_exporter', 'CSVExporterImpl'),
            'database': ('exporter.database_exporter', 'DatabaseExporterImpl')
        }
        
        if exporter_type not in exporter_map:
            print(f"Unknown exporter type: {exporter_type}")
            return None
        
        module_path, class_name = exporter_map[exporter_type]
        
        # 根据类型创建不同的实例
        if exporter_type == 'excel':
            from model.config import ExcelConfig
            excel_config = config.excel if config.excel else ExcelConfig()
            return self.load_plugin_with_params(
                module_path, 
                class_name,
                base_filename=os.path.join(config.exporter.output_dir, excel_config.file_name),
                max_rows_per_sheet=excel_config.max_rows_per_sheet
            )
        elif exporter_type == 'csv':
            return self.load_plugin_with_params(
                module_path,
                class_name,
                base_filename='s3_objects',
                output_dir=config.exporter.output_dir
            )
        elif exporter_type == 'database':
            from model.config import DatabaseConfig
            db_config = config.database if config.database else DatabaseConfig()
            return self.load_plugin_with_params(
                module_path,
                class_name,
                config=db_config
            )
        
        return None
    
    def load_plugin_with_params(
        self, 
        module_path: str, 
        class_name: str,
        *args,
        **kwargs
    ) -> Optional[Any]:
        """动态加载插件类并传入参数
        
        Args:
            module_path: 模块路径
            class_name: 类名
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            插件类实例，失败返回 None
        """
        try:
            # 导入模块
            module = importlib.import_module(module_path)
            
            # 获取类
            plugin_class = getattr(module, class_name)
            
            # 创建实例并传入参数
            instance = plugin_class(*args, **kwargs)
            
            # 缓存实例
            self.loaded_plugins[f"{module_path}.{class_name}"] = instance
            
            return instance
            
        except ImportError as e:
            print(f"Failed to import module {module_path}: {e}")
            return None
        except AttributeError as e:
            print(f"Class {class_name} not found in module {module_path}: {e}")
            return None
        except Exception as e:
            print(f"Failed to load plugin {module_path}.{class_name}: {e}")
            return None
    
    def get_plugin(self, name: str) -> Optional[Any]:
        """获取已加载的插件
        
        Args:
            name: 插件名称
            
        Returns:
            插件实例，未找到返回 None
        """
        return self.loaded_plugins.get(name)
    
    def get_all_plugins(self) -> Dict[str, Any]:
        """获取所有已加载的插件
        
        Returns:
            插件字典
        """
        return self.loaded_plugins
    
    def clear_plugins(self) -> None:
        """清除所有已加载的插件"""
        self.loaded_plugins.clear()


def create_exporter(exporter_type: str, config: Any) -> Optional[Any]:
    """工厂函数：创建导出器
    
    Args:
        exporter_type: 导出器类型
        config: 配置对象
        
    Returns:
        导出器实例
    """
    loader = PluginLoader()
    return loader.load_exporter(exporter_type, config)

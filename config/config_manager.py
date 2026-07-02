"""配置管理器模块"""
import os
import yaml
import json
import time
import threading
from typing import Union, Optional
from model.config import SystemConfig, ScannerConfig, ExporterConfig, ThreadPoolConfig, S3Config, DatabaseConfig, ExcelConfig, ConfigValidationError


class ConfigManager:
    """配置管理器接口"""
    
    def load_config(self, config_path: str) -> SystemConfig:
        """加载配置文件"""
        raise NotImplementedError
    
    def get_scanner_config(self) -> ScannerConfig:
        """获取扫描器配置"""
        raise NotImplementedError
    
    def get_exporter_config(self) -> ExporterConfig:
        """获取导出器配置"""
        raise NotImplementedError
    
    def get_thread_pool_config(self) -> ThreadPoolConfig:
        """获取线程池配置"""
        raise NotImplementedError
    
    def get_s3_config(self) -> S3Config:
        """获取S3配置"""
        raise NotImplementedError
    
    def get_database_config(self) -> Union[DatabaseConfig, None]:
        """获取数据库配置"""
        raise NotImplementedError
    
    def get_excel_config(self) -> Union[ExcelConfig, None]:
        """获取Excel配置"""
        raise NotImplementedError
    
    def start_hot_reload(self, config_path: str, callback=None) -> None:
        """启动配置热更新"""
        raise NotImplementedError
    
    def stop_hot_reload(self) -> None:
        """停止配置热更新"""
        raise NotImplementedError


class ConfigManagerImpl(ConfigManager):
    """配置管理器实现"""
    
    def __init__(self):
        self.config = SystemConfig(
            scanner=ScannerConfig(),
            exporter=ExporterConfig(),
            thread_pool=ThreadPoolConfig(),
            s3=S3Config()
        )
        self._config_path = None
        self._hot_reload_thread = None
        self._hot_reload_running = False
        self._last_mtime = None
        self._callback = None
    
    def load_config(self, config_path: str) -> SystemConfig:
        """加载配置文件"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        self._config_path = config_path
        self._last_mtime = os.path.getmtime(config_path)
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # 解析配置
        self._parse_config(data)
        
        # 验证配置
        self._validate_config()
        
        return self.config
    
    def _parse_config(self, data: dict) -> None:
        """解析配置数据"""
        # 解析scanner配置
        if 'scanner' in data:
            scanner_data = data['scanner']
            self.config.scanner = ScannerConfig(
                max_keys_per_request=scanner_data.get('maxKeysPerRequest', 1000),
                max_retries=scanner_data.get('maxRetries', 3),
                retry_delay=scanner_data.get('retryDelay', 1000),
                enable_incremental=scanner_data.get('enableIncremental', False)
            )
        
        # 解析exporter配置
        if 'exporter' in data:
            exporter_data = data['exporter']
            self.config.exporter = ExporterConfig(
                type=exporter_data.get('type', 'excel'),
                output_dir=exporter_data.get('outputDir', './output')
            )
        
        # 解析threadPool配置
        if 'threadPool' in data:
            pool_data = data['threadPool']
            self.config.thread_pool = ThreadPoolConfig(
                core_threads=pool_data.get('coreThreads', 4),
                max_threads=pool_data.get('maxThreads', 10),
                queue_size=pool_data.get('queueSize', 1000),
                keep_alive_time=pool_data.get('keepAliveTime', 60)
            )
        
        # 解析s3配置
        if 's3' in data:
            s3_data = data['s3']
            self.config.s3 = S3Config(
                endpoint=s3_data.get('endpoint'),
                region=s3_data.get('region', 'us-east-1'),
                access_key_id=s3_data.get('accessKeyId', ''),
                secret_access_key=s3_data.get('secretAccessKey', ''),
                bucket_name=s3_data.get('bucketName', ''),
                prefix=s3_data.get('prefix'),
                use_ssl=s3_data.get('useSSL', True)
            )
        
        # 解析database配置
        if 'database' in data:
            db_data = data['database']
            self.config.database = DatabaseConfig(
                type=db_data.get('type', 'mysql'),
                host=db_data.get('host', 'localhost'),
                port=db_data.get('port', 3306),
                database=db_data.get('database', ''),
                username=db_data.get('username', ''),
                password=db_data.get('password', ''),
                table_name=db_data.get('tableName', ''),
                batch_size=db_data.get('batchSize', 1000)
            )
        
        # 解析excel配置
        if 'excel' in data:
            excel_data = data['excel']
            self.config.excel = ExcelConfig(
                file_name=excel_data.get('fileName', 's3_objects'),
                max_rows_per_sheet=excel_data.get('maxRowsPerSheet', 1000000),
                split_file=excel_data.get('splitFile', True)
            )
    
    def _validate_config(self) -> None:
        """验证配置"""
        try:
            self.config.validate()
        except ConfigValidationError as e:
            raise ConfigValidationError(f"配置验证失败: {e}")
    
    def get_scanner_config(self) -> ScannerConfig:
        return self.config.scanner
    
    def get_exporter_config(self) -> ExporterConfig:
        return self.config.exporter
    
    def get_thread_pool_config(self) -> ThreadPoolConfig:
        return self.config.thread_pool
    
    def get_s3_config(self) -> S3Config:
        return self.config.s3
    
    def get_database_config(self) -> Union[DatabaseConfig, None]:
        return self.config.database
    
    def get_excel_config(self) -> Union[ExcelConfig, None]:
        return self.config.excel
    
    def start_hot_reload(self, config_path: str = None, callback=None) -> None:
        """启动配置热更新"""
        if config_path:
            self._config_path = config_path
        if callback:
            self._callback = callback
        
        if not self._config_path:
            raise ValueError("配置文件路径未设置")
        
        if not os.path.exists(self._config_path):
            raise FileNotFoundError(f"配置文件不存在: {self._config_path}")
        
        self._last_mtime = os.path.getmtime(self._config_path)
        self._hot_reload_running = True
        self._hot_reload_thread = threading.Thread(target=self._hot_reload_loop, daemon=True)
        self._hot_reload_thread.start()
    
    def _hot_reload_loop(self) -> None:
        """热更新轮询循环"""
        while self._hot_reload_running:
            try:
                if os.path.exists(self._config_path):
                    current_mtime = os.path.getmtime(self._config_path)
                    if current_mtime != self._last_mtime:
                        self._last_mtime = current_mtime
                        self._reload_config()
            except Exception as e:
                print(f"热更新检查出错: {e}")
            time.sleep(1)
    
    def _reload_config(self) -> None:
        """重新加载配置"""
        with open(self._config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        self._parse_config(data)
        self._validate_config()
        
        if self._callback:
            self._callback(self.config)
    
    def stop_hot_reload(self) -> None:
        """停止配置热更新"""
        self._hot_reload_running = False
        if self._hot_reload_thread:
            self._hot_reload_thread.join(timeout=2)

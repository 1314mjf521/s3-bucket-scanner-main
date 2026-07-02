"""配置数据模型"""
from dataclasses import dataclass
from typing import Optional, List


class ConfigValidationError(Exception):
    """配置验证异常"""
    pass


def validate_required_field(value, field_name: str) -> None:
    """验证必填字段"""
    if value is None or (isinstance(value, str) and value.strip() == ''):
        raise ConfigValidationError(f"必填字段 '{field_name}' 不能为空")


def validate_positive_integer(value, field_name: str) -> None:
    """验证正整数"""
    if not isinstance(value, int) or value <= 0:
        raise ConfigValidationError(f"字段 '{field_name}' 必须是正整数")


def validate_non_negative_integer(value, field_name: str) -> None:
    """验证非负整数"""
    if not isinstance(value, int) or value < 0:
        raise ConfigValidationError(f"字段 '{field_name}' 必须是非负整数")


def validate_boolean(value, field_name: str) -> None:
    """验证布尔值"""
    if not isinstance(value, bool):
        raise ConfigValidationError(f"字段 '{field_name}' 必须是布尔值")


def validate_in_choices(value, field_name: str, choices: List[str]) -> None:
    """验证字段值在允许的选项中"""
    if value not in choices:
        raise ConfigValidationError(f"字段 '{field_name}' 必须是以下值之一: {', '.join(choices)}")


@dataclass
class S3Config:
    """S3配置"""
    endpoint: Optional[str] = None      # S3端点URL
    region: Optional[str] = None        # 区域（可选，某些S3平台如深信服不需要）
    access_key_id: str = ''             # 访问密钥ID
    secret_access_key: str = ''         # 密钥
    bucket_name: str = ''               # 桶名称
    prefix: Optional[str] = None        # 扫描前缀
    use_ssl: bool = True                # 是否使用SSL
    
    def validate(self) -> None:
        """验证S3配置"""
        validate_required_field(self.endpoint, 'endpoint')
        validate_required_field(self.access_key_id, 'access_key_id')
        validate_required_field(self.secret_access_key, 'secret_access_key')
        validate_required_field(self.bucket_name, 'bucket_name')
        validate_boolean(self.use_ssl, 'use_ssl')


@dataclass
class ScannerConfig:
    """扫描器配置"""
    max_keys_per_request: int = 1000    # 每次请求最大键数
    max_retries: int = 5                # 最大重试次数
    retry_delay: int = 1000             # 重试延迟(毫秒)
    enable_incremental: bool = False    # 是否启用增量扫描
    
    def validate(self) -> None:
        """验证扫描器配置"""
        validate_positive_integer(self.max_keys_per_request, 'max_keys_per_request')
        validate_positive_integer(self.max_retries, 'max_retries')
        validate_non_negative_integer(self.retry_delay, 'retry_delay')
        validate_boolean(self.enable_incremental, 'enable_incremental')


@dataclass
class ExporterConfig:
    """导出器配置"""
    type: str = 'excel'                 # 导出类型: excel 或 database
    output_dir: str = './output'        # 输出目录
    
    def validate(self) -> None:
        """验证导出器配置"""
        validate_in_choices(self.type, 'type', ['excel', 'database', 'csv'])
        validate_required_field(self.output_dir, 'output_dir')


@dataclass
class DatabaseConfig:
    """数据库导出配置"""
    type: str = 'mysql'                 # 数据库类型
    host: str = 'localhost'
    port: int = 3306
    database: str = ''
    username: str = ''
    password: str = ''
    table_name: str = ''
    batch_size: int = 1000
    
    def validate(self) -> None:
        """验证数据库配置"""
        validate_in_choices(self.type, 'type', ['mysql', 'postgresql'])
        validate_required_field(self.host, 'host')
        validate_positive_integer(self.port, 'port')
        validate_required_field(self.database, 'database')
        validate_required_field(self.username, 'username')
        validate_required_field(self.password, 'password')
        validate_required_field(self.table_name, 'table_name')
        validate_positive_integer(self.batch_size, 'batch_size')


@dataclass
class ExcelConfig:
    """Excel导出配置"""
    file_name: str = 's3_objects'
    max_rows_per_sheet: int = 1000000
    split_file: bool = True
    
    def validate(self) -> None:
        """验证Excel配置"""
        validate_required_field(self.file_name, 'file_name')
        validate_positive_integer(self.max_rows_per_sheet, 'max_rows_per_sheet')
        validate_boolean(self.split_file, 'split_file')


@dataclass
class ThreadPoolConfig:
    """线程池配置"""
    core_threads: int = 4               # 核心线程数
    max_threads: int = 10               # 最大线程数
    queue_size: int = 1000              # 队列大小
    keep_alive_time: int = 60           # 线程存活时间(秒)
    
    def validate(self) -> None:
        """验证线程池配置"""
        validate_positive_integer(self.core_threads, 'core_threads')
        validate_positive_integer(self.max_threads, 'max_threads')
        if self.max_threads < self.core_threads:
            raise ConfigValidationError("max_threads 必须大于或等于 core_threads")
        validate_positive_integer(self.queue_size, 'queue_size')
        validate_non_negative_integer(self.keep_alive_time, 'keep_alive_time')


@dataclass
class SystemConfig:
    """系统配置"""
    scanner: ScannerConfig
    exporter: ExporterConfig
    thread_pool: ThreadPoolConfig
    s3: S3Config
    database: Optional[DatabaseConfig] = None
    excel: Optional[ExcelConfig] = None
    
    def validate(self) -> None:
        """验证系统配置"""
        self.scanner.validate()
        self.exporter.validate()
        self.thread_pool.validate()
        self.s3.validate()
        
        # 根据导出类型验证相应配置
        if self.exporter.type == 'database' and self.database is None:
            raise ConfigValidationError("当 exporter.type 为 'database' 时，必须提供 database 配置")
        if self.exporter.type == 'excel' and self.excel is None:
            raise ConfigValidationError("当 exporter.type 为 'excel' 时，必须提供 excel 配置")
        
        if self.database:
            self.database.validate()
        if self.excel:
            self.excel.validate()

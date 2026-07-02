"""S3对象数据模型"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class S3Object:
    """S3对象数据模型"""
    key: str           # 文件名
    bucket: str        # 桶名称
    path: str          # 完整路径
    last_modified: datetime  # 上传时间
    size: int          # 文件大小
    etag: str          # ETag


@dataclass
class ScanProgress:
    """扫描进度信息"""
    total_objects: int      # 总对象数
    scanned_objects: int    # 已扫描对象数
    current_prefix: Optional[str] = None  # 当前扫描前缀
    start_time: datetime = datetime.now()  # 开始时间
    last_update: datetime = datetime.now()  # 最后更新时间
    errors: int = 0         # 错误数量

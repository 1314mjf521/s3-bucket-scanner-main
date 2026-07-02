"""S3扫描器模块"""
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional
from model.s3_object import S3Object, ScanProgress
from model.config import S3Config


class S3Credentials:
    """S3凭证"""
    def __init__(
        self,
        access_key_id: str,
        secret_access_key: str,
        endpoint: Optional[str] = None,
        region: str = 'us-east-1',
        use_ssl: bool = True
    ):
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.endpoint = endpoint
        self.region = region
        self.use_ssl = use_ssl


class S3Scanner(ABC):
    """S3扫描器接口"""
    
    @abstractmethod
    async def connect(self, bucket_name: str, credentials: S3Credentials) -> None:
        """连接到S3桶"""
        pass
    
    @abstractmethod
    async def scan_objects(self, prefix: Optional[str] = None) -> AsyncIterator[S3Object]:
        """扫描S3对象"""
        pass
    
    @abstractmethod
    def get_progress(self) -> ScanProgress:
        """获取扫描进度"""
        pass
    
    @abstractmethod
    def pause(self) -> None:
        """暂停扫描"""
        pass
    
    @abstractmethod
    def resume(self) -> None:
        """恢复扫描"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        pass

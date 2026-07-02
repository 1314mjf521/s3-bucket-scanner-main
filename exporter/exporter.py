"""数据导出器模块"""
from abc import ABC, abstractmethod
from typing import List
from model.s3_object import S3Object


class Exporter(ABC):
    """导出器接口"""
    
    @abstractmethod
    async def open(self) -> None:
        """打开导出器"""
        pass
    
    @abstractmethod
    async def write(self, data: List[S3Object]) -> None:
        """写入数据"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """关闭导出器"""
        pass


class ExcelExporter(Exporter):
    """Excel导出器接口"""
    
    @abstractmethod
    def set_file_name(self, file_name: str) -> None:
        """设置文件名"""
        pass
    
    @abstractmethod
    def set_max_rows_per_sheet(self, max_rows: int) -> None:
        """设置每张表最大行数"""
        pass


class DatabaseExporter(Exporter):
    """数据库导出器接口"""
    
    @abstractmethod
    def set_table_name(self, table_name: str) -> None:
        """设置表名"""
        pass
    
    @abstractmethod
    def set_batch_size(self, batch_size: int) -> None:
        """设置批量大小"""
        pass

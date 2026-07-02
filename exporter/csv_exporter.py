"""CSV导出器实现"""
import os
import csv
from datetime import datetime
from typing import List, Optional
from model.s3_object import S3Object
from exporter.exporter import Exporter


class CSVExporterImpl(Exporter):
    """CSV导出器实现"""
    
    def __init__(
        self,
        base_filename: str = 's3_objects_export',
        output_dir: str = './output'
    ):
        self.base_filename = base_filename
        self.output_dir = output_dir
        self.file_path: Optional[str] = None
        self.file_handle = None
        self.writer = None
        self.is_open = False
        self.row_count = 0
        
    async def open(self) -> None:
        """打开导出器"""
        # 确保输出目录存在
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # 生成文件路径
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.file_path = os.path.join(self.output_dir, f'{self.base_filename}_{timestamp}.csv')
        
        # 创建 CSV 文件
        self.file_handle = open(self.file_path, 'w', newline='', encoding='utf-8-sig')
        self.writer = csv.writer(self.file_handle)
        
        # 写入表头
        self.writer.writerow(['Key', 'Bucket', 'Path', 'Last Modified', 'Size (bytes)', 'ETag'])
        
        self.is_open = True
        self.row_count = 0
        
    async def write(self, data: List[S3Object]) -> None:
        """写入数据（批量）"""
        if not self.is_open:
            raise RuntimeError("Exporter is not open. Call open() first.")
            
        if not data:
            return
        
        # 批量写入
        for obj in data:
            self.writer.writerow([
                obj.key,
                obj.bucket,
                obj.path,
                obj.last_modified,
                obj.size,
                obj.etag
            ])
            self.row_count += 1
        
        # 立即刷新到磁盘，确保数据写入
        if self.file_handle:
            self.file_handle.flush()
            os.fsync(self.file_handle.fileno())
        
    async def close(self) -> List[str]:
        """关闭导出器并保存文件"""
        if not self.is_open:
            return []
            
        if self.file_handle:
            self.file_handle.close()
        
        self.is_open = False
        self.file_handle = None
        self.writer = None
        
        # 返回保存的文件列表
        if self.file_path:
            return [self.file_path]
        return []
    
    def set_file_name(self, file_name: str) -> None:
        """设置文件名"""
        self.base_filename = file_name
        
    def set_max_rows_per_sheet(self, max_rows: int) -> None:
        """设置每张表最大行数（CSV 无此限制）"""
        pass

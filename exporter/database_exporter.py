"""数据库导出器实现"""
from typing import List, Optional
from model.s3_object import S3Object
from model.config import DatabaseConfig
from exporter.exporter import DatabaseExporter
from exporter.database_connector import create_database_connector, DatabaseConnector


class DatabaseExporterImpl(DatabaseExporter):
    """数据库导出器实现"""
    
    def __init__(
        self,
        config: DatabaseConfig,
        table_name: Optional[str] = None,
        batch_size: Optional[int] = None
    ):
        self.config = config
        self.table_name = table_name or config.table_name
        self.batch_size = batch_size or config.batch_size
        self.connector: Optional[DatabaseConnector] = None
        self.is_open = False
        self._buffer: List[S3Object] = []
        self._total_rows_written = 0
        self._batch_count = 0
    
    async def open(self) -> None:
        """打开导出器"""
        self.connector = create_database_connector(self.config)
        await self.connector.connect()
        
        # 创建表
        columns = [
            "`key` VARCHAR(1024) NOT NULL",
            "`bucket` VARCHAR(255) NOT NULL",
            "`path` TEXT",
            "`last_modified` DATETIME NOT NULL",
            "`size` BIGINT DEFAULT 0",
            "`etag` VARCHAR(255)",
            "PRIMARY KEY (`key`, `bucket`)"
        ]
        await self.connector.create_table_if_not_exists(self.table_name, columns)
        
        self.is_open = True
        self._buffer = []
        self._total_rows_written = 0
        self._batch_count = 0
    
    async def write(self, data: List[S3Object]) -> None:
        """写入数据（批量）"""
        if not self.is_open or self.connector is None:
            raise RuntimeError("Exporter is not open. Call open() first.")
        
        if not data:
            return
        
        self._buffer.extend(data)
        
        # 达到批量大小时写入
        if len(self._buffer) >= self.batch_size:
            await self._flush_buffer()
    
    async def close(self) -> int:
        """关闭导出器，返回写入的总行数"""
        if not self.is_open:
            return 0
        
        # 写入剩余数据
        if self._buffer:
            await self._flush_buffer()
        
        self.is_open = False
        await self.connector.disconnect()
        self.connector = None
        
        return self._total_rows_written
    
    async def _flush_buffer(self) -> None:
        """刷新缓冲区到数据库"""
        if not self._buffer:
            return
        
        # 开始事务
        await self.connector.begin_transaction()
        
        try:
            # 构建批量插入SQL
            placeholders = ', '.join(['(%s, %s, %s, %s, %s, %s)'] * len(self._buffer))
            columns = '`key`, `bucket`, `path`, `last_modified`, `size`, `etag`'
            values = []
            
            for obj in self._buffer:
                values.extend([
                    obj.key,
                    obj.bucket,
                    obj.path,
                    obj.last_modified,
                    obj.size,
                    obj.etag
                ])
            
            sql = f"""
                INSERT INTO `{self.table_name}` ({columns})
                VALUES {placeholders}
                ON DUPLICATE KEY UPDATE
                    `path` = VALUES(`path`),
                    `last_modified` = VALUES(`last_modified`),
                    `size` = VALUES(`size`),
                    `etag` = VALUES(`etag`)
            """
            
            await self.connector.execute(sql, tuple(values))
            await self.connector.commit()
            
            self._total_rows_written += len(self._buffer)
            self._batch_count += 1
            self._buffer = []
            
        except Exception as e:
            await self.connector.rollback()
            raise RuntimeError(f"Failed to write batch: {e}")
    
    def set_table_name(self, table_name: str) -> None:
        """设置表名"""
        self.table_name = table_name
    
    def set_batch_size(self, batch_size: int) -> None:
        """设置批量大小"""
        self.batch_size = batch_size

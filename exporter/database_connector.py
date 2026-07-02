"""数据库连接器模块"""
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

try:
    import aiomysql
    AIOMYSQL_AVAILABLE = True
except ImportError:
    AIOMYSQL_AVAILABLE = False

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False

from model.config import DatabaseConfig


class DatabaseConnectionError(Exception):
    """数据库连接错误"""
    pass


class DatabaseConnector(ABC):
    """数据库连接器接口"""
    
    @abstractmethod
    async def connect(self) -> None:
        """连接数据库"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """断开数据库连接"""
        pass
    
    @abstractmethod
    @asynccontextmanager
    async def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        pass
    
    @abstractmethod
    async def execute(self, query: str, params: Optional[tuple] = None) -> int:
        """执行SQL语句，返回影响的行数"""
        pass
    
    @abstractmethod
    async def fetchall(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """执行查询，返回所有结果"""
        pass
    
    @abstractmethod
    async def fetchone(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """执行查询，返回单条结果"""
        pass
    
    @abstractmethod
    async def begin_transaction(self) -> None:
        """开始事务"""
        pass
    
    @abstractmethod
    async def commit(self) -> None:
        """提交事务"""
        pass
    
    @abstractmethod
    async def rollback(self) -> None:
        """回滚事务"""
        pass
    
    @abstractmethod
    async def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        pass
    
    @abstractmethod
    async def create_table_if_not_exists(self, table_name: str, columns: List[str]) -> None:
        """如果表不存在则创建表"""
        pass


class MySQLConnector(DatabaseConnector):
    """MySQL数据库连接器"""
    
    def __init__(self, config: DatabaseConfig):
        if not AIOMYSQL_AVAILABLE:
            raise ImportError("aiomysql is not installed. Install it with: pip install aiomysql")
        
        self.config = config
        self.pool: Optional[aiomysql.Pool] = None
        self._connection: Optional[aiomysql.Connection] = None
        self._in_transaction = False
    
    async def connect(self) -> None:
        """连接数据库"""
        try:
            self.pool = await aiomysql.create_pool(
                host=self.config.host,
                port=self.config.port,
                user=self.config.username,
                password=self.config.password,
                db=self.config.database,
                minsize=1,
                maxsize=self.config.batch_size,
                autocommit=False,
                connect_timeout=30
            )
        except Exception as e:
            raise DatabaseConnectionError(f"Failed to connect to MySQL: {e}")
    
    async def disconnect(self) -> None:
        """断开数据库连接"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None
    
    @asynccontextmanager
    async def get_connection(self):
        """获取数据库连接"""
        if self._in_transaction and self._connection:
            yield self._connection
        else:
            if self.pool is None:
                raise DatabaseConnectionError("Database is not connected")
            conn = await self.pool.acquire()
            try:
                yield conn
            finally:
                if not self._in_transaction:
                    await self.pool.release(conn)
    
    async def execute(self, query: str, params: Optional[tuple] = None) -> int:
        """执行SQL语句"""
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params or ())
                await conn.commit()
                return cursor.rowcount
    
    async def fetchall(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """执行查询，返回所有结果"""
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params or ())
                return await cursor.fetchall()
    
    async def fetchone(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """执行查询，返回单条结果"""
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params or ())
                return await cursor.fetchone()
    
    async def begin_transaction(self) -> None:
        """开始事务"""
        if self.pool is None:
            raise DatabaseConnectionError("Database is not connected")
        self._connection = await self.pool.acquire()
        self._in_transaction = True
    
    async def commit(self) -> None:
        """提交事务"""
        if self._connection and self._in_transaction:
            await self._connection.commit()
            await self.pool.release(self._connection)
            self._connection = None
            self._in_transaction = False
    
    async def rollback(self) -> None:
        """回滚事务"""
        if self._connection and self._in_transaction:
            await self._connection.rollback()
            await self.pool.release(self._connection)
            self._connection = None
            self._in_transaction = False
    
    async def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        query = """
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = %s AND table_name = %s
        """
        result = await self.fetchone(query, (self.config.database, table_name))
        return result is not None and result.get('COUNT(*)', 0) > 0
    
    async def create_table_if_not_exists(self, table_name: str, columns: List[str]) -> None:
        """如果表不存在则创建表"""
        if await self.table_exists(table_name):
            return
        
        columns_def = ', '.join(columns)
        create_sql = f"CREATE TABLE `{table_name}` ({columns_def})"
        await self.execute(create_sql)


class PostgreSQLConnector(DatabaseConnector):
    """PostgreSQL数据库连接器"""
    
    def __init__(self, config: DatabaseConfig):
        if not ASYNCPG_AVAILABLE:
            raise ImportError("asyncpg is not installed. Install it with: pip install asyncpg")
        
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None
        self._connection: Optional[asyncpg.Connection] = None
        self._in_transaction = False
        self._transaction: Optional[asyncpg.Transaction] = None
    
    async def connect(self) -> None:
        """连接数据库"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                user=self.config.username,
                password=self.config.password,
                database=self.config.database,
                min_size=1,
                max_size=self.config.batch_size,
                command_timeout=60
            )
        except Exception as e:
            raise DatabaseConnectionError(f"Failed to connect to PostgreSQL: {e}")
    
    async def disconnect(self) -> None:
        """断开数据库连接"""
        if self.pool:
            await self.pool.close()
            self.pool = None
    
    @asynccontextmanager
    async def get_connection(self):
        """获取数据库连接"""
        if self._in_transaction and self._connection:
            yield self._connection
        else:
            if self.pool is None:
                raise DatabaseConnectionError("Database is not connected")
            conn = await self.pool.acquire()
            try:
                yield conn
            finally:
                if not self._in_transaction:
                    await self.pool.release(conn)
    
    async def execute(self, query: str, params: Optional[tuple] = None) -> int:
        """执行SQL语句"""
        async with self.get_connection() as conn:
            if params is None:
                params = ()
            result = await conn.execute(query, *params)
            # asyncpg returns ExecuteCommandComplete, extract row count
            return int(result.split()[-1]) if result else 0
    
    async def fetchall(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """执行查询，返回所有结果"""
        async with self.get_connection() as conn:
            if params is None:
                params = ()
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    async def fetchone(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """执行查询，返回单条结果"""
        async with self.get_connection() as conn:
            if params is None:
                params = ()
            row = await conn.fetchrow(query, *params)
            return dict(row) if row else None
    
    async def begin_transaction(self) -> None:
        """开始事务"""
        if self.pool is None:
            raise DatabaseConnectionError("Database is not connected")
        self._connection = await self.pool.acquire()
        self._transaction = self._connection.transaction()
        await self._transaction.start()
        self._in_transaction = True
    
    async def commit(self) -> None:
        """提交事务"""
        if self._transaction and self._in_transaction:
            await self._transaction.commit()
            await self.pool.release(self._connection)
            self._connection = None
            self._transaction = None
            self._in_transaction = False
    
    async def rollback(self) -> None:
        """回滚事务"""
        if self._transaction and self._in_transaction:
            await self._transaction.rollback()
            await self.pool.release(self._connection)
            self._connection = None
            self._transaction = None
            self._in_transaction = False
    
    async def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        query = """
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = $1
        """
        result = await self.fetchone(query, (table_name,))
        return result is not None and result.get('count', 0) > 0
    
    async def create_table_if_not_exists(self, table_name: str, columns: List[str]) -> None:
        """如果表不存在则创建表"""
        if await self.table_exists(table_name):
            return
        
        columns_def = ', '.join(columns)
        create_sql = f"CREATE TABLE IF NOT EXISTS \"{table_name}\" ({columns_def})"
        await self.execute(create_sql)


def create_database_connector(config: DatabaseConfig) -> DatabaseConnector:
    """创建数据库连接器工厂函数"""
    if config.type == 'mysql':
        return MySQLConnector(config)
    elif config.type == 'postgresql':
        return PostgreSQLConnector(config)
    else:
        raise ValueError(f"Unsupported database type: {config.type}")

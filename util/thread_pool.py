"""线程池模块"""
from abc import ABC, abstractmethod
from typing import TypeVar, Callable, Awaitable
import asyncio
from dataclasses import dataclass


T = TypeVar('T')


@dataclass
class ThreadPoolOptions:
    """线程池配置选项"""
    core_threads: int = 4
    max_threads: int = 10
    queue_size: int = 1000
    keep_alive_time: int = 60


class ThreadPool(ABC):
    """线程池接口"""
    
    @abstractmethod
    async def submit(self, task: Callable[[], Awaitable[T]]) -> T:
        """提交任务"""
        pass
    
    @abstractmethod
    async def submit_void(self, task: Callable[[], Awaitable[None]]) -> None:
        """提交无返回值任务"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """关闭线程池"""
        pass
    
    @abstractmethod
    async def await_termination(self, timeout: int) -> bool:
        """等待终止"""
        pass
    
    @abstractmethod
    def get_active_count(self) -> int:
        """获取活动线程数"""
        pass
    
    @abstractmethod
    def get_queue_size(self) -> int:
        """获取队列大小"""
        pass


class ThreadPoolImpl(ThreadPool):
    """线程池实现"""
    
    def __init__(self, options: ThreadPoolOptions):
        self.options = options
        self.active_count = 0
        self.queue_size = 0
        self.is_shutdown = False
        self._semaphore = asyncio.Semaphore(options.max_threads)
    
    async def submit(self, task: Callable[[], Awaitable[T]]) -> T:
        """提交任务并返回结果"""
        if self.is_shutdown:
            raise RuntimeError("线程池已关闭")
        
        self.active_count += 1
        self.queue_size += 1
        
        try:
            async with self._semaphore:
                result = await task()
                return result
        finally:
            self.active_count -= 1
            self.queue_size -= 1
    
    async def submit_void(self, task: Callable[[], Awaitable[None]]) -> None:
        """提交无返回值任务"""
        if self.is_shutdown:
            raise RuntimeError("线程池已关闭")
        
        self.active_count += 1
        self.queue_size += 1
        
        try:
            async with self._semaphore:
                await task()
        except Exception as e:
            print(f"DEBUG: Error in thread pool task: {e}")
            raise
        finally:
            self.active_count -= 1
            self.queue_size -= 1
    
    async def shutdown(self) -> None:
        """关闭线程池"""
        self.is_shutdown = True
    
    async def await_termination(self, timeout: int) -> bool:
        """等待终止"""
        # 简化实现，实际应等待所有任务完成
        return True
    
    def get_active_count(self) -> int:
        """获取活动线程数"""
        return self.active_count
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        return self.queue_size

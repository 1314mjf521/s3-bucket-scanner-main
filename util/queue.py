"""线程安全队列模块"""
from typing import TypeVar, Generic, Optional, List
from dataclasses import dataclass, field
import threading
import queue
import time


T = TypeVar('T')


@dataclass
class TaskResult(Generic[T]):
    """任务结果"""
    task_id: str
    result: Optional[T] = None
    error: Optional[Exception] = None
    completed: bool = False


class ThreadSafeQueue(Generic[T]):
    """线程安全队列"""
    
    def __init__(self, max_size: int = 1000):
        self._queue: queue.Queue = queue.Queue(maxsize=max_size)
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)
        self._size = 0
        self._max_size = max_size
    
    def put(self, item: T, timeout: Optional[float] = None) -> bool:
        """添加元素到队列"""
        with self._not_full:
            if timeout is not None:
                if not self._not_full.wait_for(lambda: self._size < self._max_size, timeout=timeout):
                    return False
            else:
                while self._size >= self._max_size:
                    self._not_full.wait()
            
            self._queue.put(item)
            self._size += 1
            self._not_empty.notify()
            return True
    
    def get(self, timeout: Optional[float] = None) -> Optional[T]:
        """从队列获取元素"""
        with self._not_empty:
            if timeout is not None:
                if not self._not_empty.wait_for(lambda: self._size > 0, timeout=timeout):
                    return None
            else:
                while self._size == 0:
                    self._not_empty.wait()
            
            item = self._queue.get()
            self._size -= 1
            self._not_full.notify()
            return item
    
    def put_nowait(self, item: T) -> bool:
        """非阻塞添加元素"""
        with self._not_full:
            if self._size >= self._max_size:
                return False
            self._queue.put_nowait(item)
            self._size += 1
            self._not_empty.notify()
            return True
    
    def get_nowait(self) -> Optional[T]:
        """非阻塞获取元素"""
        with self._not_empty:
            if self._size == 0:
                return None
            item = self._queue.get_nowait()
            self._size -= 1
            self._not_full.notify()
            return item
    
    def size(self) -> int:
        """获取队列大小"""
        with self._lock:
            return self._size
    
    def empty(self) -> bool:
        """队列是否为空"""
        with self._lock:
            return self._size == 0
    
    def full(self) -> bool:
        """队列是否已满"""
        with self._lock:
            return self._size >= self._max_size
    
    def clear(self) -> None:
        """清空队列"""
        with self._lock:
            self._queue.queue.clear()
            self._size = 0


class TaskQueue(Generic[T]):
    """任务队列，支持任务追踪"""
    
    def __init__(self, max_size: int = 1000):
        self._queue: ThreadSafeQueue[TaskResult[T]] = ThreadSafeQueue(max_size)
        self._task_results: dict = {}
        self._lock = threading.Lock()
        self._task_counter = 0
    
    def submit(self, task_id: str, task_func) -> None:
        """提交任务"""
        with self._lock:
            self._task_counter += 1
            task_result = TaskResult(task_id=task_id)
            self._task_results[task_id] = task_result
        
        self._queue.put(task_result)
    
    def get_task(self, timeout: Optional[float] = None) -> Optional[TaskResult[T]]:
        """获取任务"""
        return self._queue.get(timeout)
    
    def complete_task(self, task_id: str, result: Optional[T] = None, error: Optional[Exception] = None) -> bool:
        """完成任务"""
        with self._lock:
            if task_id in self._task_results:
                self._task_results[task_id].result = result
                self._task_results[task_id].error = error
                self._task_results[task_id].completed = True
                return True
        return False
    
    def get_task_result(self, task_id: str) -> Optional[TaskResult[T]]:
        """获取任务结果"""
        with self._lock:
            return self._task_results.get(task_id)
    
    def size(self) -> int:
        """获取队列大小"""
        return self._queue.size()
    
    def pending_count(self) -> int:
        """获取待处理任务数"""
        with self._lock:
            return len([r for r in self._task_results.values() if not r.completed])


class BoundedBlockingQueue(Generic[T]):
    """有界阻塞队列，用于生产者-消费者模式"""
    
    def __init__(self, max_size: int = 1000):
        self._queue: queue.Queue = queue.Queue(maxsize=max_size)
        self._shutdown = False
        self._shutdown_lock = threading.Lock()
    
    def put(self, item: T, timeout: Optional[float] = None) -> bool:
        """添加元素"""
        if self._shutdown:
            raise RuntimeError("Queue is shutdown")
        
        try:
            if timeout is not None:
                self._queue.put(item, timeout=timeout)
            else:
                self._queue.put(item, block=True)
            return True
        except queue.Full:
            return False
    
    def get(self, timeout: Optional[float] = None) -> Optional[T]:
        """获取元素"""
        try:
            if timeout is not None:
                return self._queue.get(timeout=timeout)
            else:
                return self._queue.get(block=True)
        except queue.Empty:
            return None
    
    def put_nowait(self, item: T) -> bool:
        """非阻塞添加"""
        if self._shutdown:
            raise RuntimeError("Queue is shutdown")
        try:
            self._queue.put_nowait(item)
            return True
        except queue.Full:
            return False
    
    def get_nowait(self) -> Optional[T]:
        """非阻塞获取"""
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None
    
    def shutdown(self) -> None:
        """关闭队列"""
        with self._shutdown_lock:
            self._shutdown = True
    
    def is_shutdown(self) -> bool:
        """是否已关闭"""
        with self._shutdown_lock:
            return self._shutdown
    
    def size(self) -> int:
        """队列大小"""
        return self._queue.qsize()

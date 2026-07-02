"""Tests for thread pool"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from util.thread_pool import ThreadPoolImpl, ThreadPoolOptions


class TestThreadPoolOptions:
    """Tests for ThreadPoolOptions"""
    
    def test_default_values(self):
        """Test ThreadPoolOptions with default values"""
        options = ThreadPoolOptions()
        
        assert options.core_threads == 4
        assert options.max_threads == 10
        assert options.queue_size == 1000
        assert options.keep_alive_time == 60
    
    def test_custom_values(self):
        """Test ThreadPoolOptions with custom values"""
        options = ThreadPoolOptions(
            core_threads=8,
            max_threads=20,
            queue_size=500,
            keep_alive_time=120
        )
        
        assert options.core_threads == 8
        assert options.max_threads == 20
        assert options.queue_size == 500
        assert options.keep_alive_time == 120


class TestThreadPoolImpl:
    """Tests for ThreadPoolImpl"""
    
    def test_initialization(self):
        """Test ThreadPoolImpl initialization"""
        options = ThreadPoolOptions(
            core_threads=4,
            max_threads=10,
            queue_size=1000,
            keep_alive_time=60
        )
        
        pool = ThreadPoolImpl(options)
        
        assert pool.options == options
        assert pool.active_count == 0
        assert pool.queue_size == 0
        assert pool.is_shutdown == False
    
    @pytest.mark.asyncio
    async def test_submit_success(self):
        """Test submitting a successful task"""
        options = ThreadPoolOptions(core_threads=2, max_threads=4)
        pool = ThreadPoolImpl(options)
        
        async def sample_task():
            await asyncio.sleep(0.01)
            return 'result'
        
        result = await pool.submit(sample_task)
        
        assert result == 'result'
        assert pool.active_count == 0  # Should be reset after completion
        assert pool.queue_size == 0
    
    @pytest.mark.asyncio
    async def test_submit_void_success(self):
        """Test submitting a void task"""
        options = ThreadPoolOptions(core_threads=2, max_threads=4)
        pool = ThreadPoolImpl(options)
        
        result = None
        
        async def sample_void_task():
            nonlocal result
            await asyncio.sleep(0.01)
            result = 'executed'
        
        await pool.submit_void(sample_void_task)
        
        assert result == 'executed'
        assert pool.active_count == 0
        assert pool.queue_size == 0
    
    @pytest.mark.asyncio
    async def test_submit_concurrent_tasks(self):
        """Test submitting multiple concurrent tasks"""
        options = ThreadPoolOptions(core_threads=2, max_threads=4)
        pool = ThreadPoolImpl(options)
        
        results = []
        
        async def sample_task(n):
            await asyncio.sleep(0.01)
            return n * 2
        
        # Pass the coroutine function, not the result
        tasks = [pool.submit(lambda n=i: sample_task(n)) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        assert results == [0, 2, 4, 6, 8]
    
    @pytest.mark.asyncio
    async def test_submit_after_shutdown(self):
        """Test submitting task after shutdown"""
        options = ThreadPoolOptions(core_threads=2, max_threads=4)
        pool = ThreadPoolImpl(options)
        
        await pool.shutdown()
        
        async def sample_task():
            return 'result'
        
        with pytest.raises(RuntimeError, match='线程池已关闭'):
            await pool.submit(sample_task)
    
    @pytest.mark.asyncio
    async def test_submit_void_after_shutdown(self):
        """Test submitting void task after shutdown"""
        options = ThreadPoolOptions(core_threads=2, max_threads=4)
        pool = ThreadPoolImpl(options)
        
        await pool.shutdown()
        
        async def sample_void_task():
            pass
        
        with pytest.raises(RuntimeError, match='线程池已关闭'):
            await pool.submit_void(sample_void_task)
    
    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test shutting down thread pool"""
        options = ThreadPoolOptions(core_threads=2, max_threads=4)
        pool = ThreadPoolImpl(options)
        
        assert pool.is_shutdown == False
        
        await pool.shutdown()
        
        assert pool.is_shutdown == True
    
    @pytest.mark.asyncio
    async def test_await_termination(self):
        """Test awaiting termination"""
        options = ThreadPoolOptions(core_threads=2, max_threads=4)
        pool = ThreadPoolImpl(options)
        
        result = await pool.await_termination(5)
        
        assert result == True
    
    def test_get_active_count(self):
        """Test getting active thread count"""
        options = ThreadPoolOptions(core_threads=2, max_threads=4)
        pool = ThreadPoolImpl(options)
        
        assert pool.get_active_count() == 0
    
    def test_get_queue_size(self):
        """Test getting queue size"""
        options = ThreadPoolOptions(core_threads=2, max_threads=4)
        pool = ThreadPoolImpl(options)
        
        assert pool.get_queue_size() == 0
    
    @pytest.mark.asyncio
    async def test_task_exception_handling(self):
        """Test handling exceptions in tasks"""
        options = ThreadPoolOptions(core_threads=2, max_threads=4)
        pool = ThreadPoolImpl(options)
        
        async def failing_task():
            raise ValueError('Test error')
        
        with pytest.raises(ValueError, match='Test error'):
            await pool.submit(failing_task)
        
        # Pool should still be functional after exception
        async def success_task():
            return 'success'
        
        result = await pool.submit(success_task)
        assert result == 'success'

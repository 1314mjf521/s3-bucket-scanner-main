"""Performance tests for S3 Bucket Scanner"""
import pytest
import asyncio
import time
import tracemalloc
import tempfile
import os
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from scanner.s3_scanner_impl import S3ScannerImpl
from exporter.excel_exporter import ExcelExporterImpl
from model.config import SystemConfig, ScannerConfig, ExporterConfig, ThreadPoolConfig, S3Config, ExcelConfig
from model.s3_object import S3Object


class TestPerformanceScan:
    """Performance tests for scanning functionality"""
    
    @pytest.mark.asyncio
    async def test_scan_performance_1000_objects(self):
        """Test scanning performance with 1000 objects"""
        config = SystemConfig(
            scanner=ScannerConfig(max_keys_per_request=1000),
            exporter=ExporterConfig(type='excel'),
            thread_pool=ThreadPoolConfig(),
            s3=S3Config(
                endpoint='http://localhost:9000',
                region='us-east-1',
                access_key_id='test-key',
                secret_access_key='test-secret',
                bucket_name='test-bucket'
            ),
            excel=ExcelConfig()
        )
        
        scanner = S3ScannerImpl(config.s3, config.scanner)
        
        # Generate 1000 mock objects
        mock_objects = []
        for i in range(1000):
            mock_objects.append({
                'Key': f'folder/file_{i:04d}.txt',
                'LastModified': datetime.now(),
                'Size': 1024,
                'ETag': f'etag-{i}'
            })
        
        with patch.object(scanner.client, 'connect', return_value=True):
            with patch.object(scanner.client, 'is_connected', return_value=True):
                with patch.object(scanner.client, 'list_objects', return_value={
                    'KeyCount': 1000,
                    'Contents': mock_objects,
                    'IsTruncated': False
                }):
                    start_time = time.time()
                    
                    count = 0
                    async for obj in scanner.scan_objects():
                        count += 1
                    
                    elapsed_time = time.time() - start_time
                    
                    assert count == 1000
                    # Should complete in reasonable time (less than 10 seconds for 1000 objects)
                    assert elapsed_time < 10, f"Scan took {elapsed_time:.2f}s, expected < 10s"
    
    @pytest.mark.asyncio
    async def test_scan_performance_10000_objects(self):
        """Test scanning performance with 10000 objects"""
        config = SystemConfig(
            scanner=ScannerConfig(max_keys_per_request=1000),
            exporter=ExporterConfig(type='excel'),
            thread_pool=ThreadPoolConfig(),
            s3=S3Config(
                endpoint='http://localhost:9000',
                region='us-east-1',
                access_key_id='test-key',
                secret_access_key='test-secret',
                bucket_name='test-bucket'
            ),
            excel=ExcelConfig()
        )
        
        scanner = S3ScannerImpl(config.s3, config.scanner)
        
        # Generate 10000 mock objects
        mock_objects = []
        for i in range(10000):
            mock_objects.append({
                'Key': f'folder/file_{i:04d}.txt',
                'LastModified': datetime.now(),
                'Size': 1024,
                'ETag': f'etag-{i}'
            })
        
        with patch.object(scanner.client, 'connect', return_value=True):
            with patch.object(scanner.client, 'is_connected', return_value=True):
                with patch.object(scanner.client, 'list_objects', return_value={
                    'KeyCount': 10000,
                    'Contents': mock_objects,
                    'IsTruncated': False
                }):
                    start_time = time.time()
                    
                    count = 0
                    async for obj in scanner.scan_objects():
                        count += 1
                    
                    elapsed_time = time.time() - start_time
                    
                    assert count == 10000
                    # Should complete in reasonable time (less than 30 seconds for 10000 objects)
                    assert elapsed_time < 30, f"Scan took {elapsed_time:.2f}s, expected < 30s"
    
    @pytest.mark.asyncio
    async def test_scan_memory_efficiency(self):
        """Test that scanning is memory efficient with large datasets"""
        config = SystemConfig(
            scanner=ScannerConfig(max_keys_per_request=100),
            exporter=ExporterConfig(type='excel'),
            thread_pool=ThreadPoolConfig(),
            s3=S3Config(
                endpoint='http://localhost:9000',
                region='us-east-1',
                access_key_id='test-key',
                secret_access_key='test-secret',
                bucket_name='test-bucket'
            ),
            excel=ExcelConfig()
        )
        
        scanner = S3ScannerImpl(config.s3, config.scanner)
        
        # Generate 10000 mock objects in pages
        all_objects = []
        for i in range(10000):
            all_objects.append({
                'Key': f'folder/file_{i:04d}.txt',
                'LastModified': datetime.now(),
                'Size': 1024,
                'ETag': f'etag-{i}'
            })
        
        # Simulate paginated responses
        pages = []
        for i in range(0, 10000, 100):
            page_objects = all_objects[i:i+100]
            pages.append({
                'KeyCount': len(page_objects),
                'Contents': page_objects,
                'IsTruncated': i + 100 < 10000
            })
        
        with patch.object(scanner.client, 'connect', return_value=True):
            with patch.object(scanner.client, 'is_connected', return_value=True):
                with patch.object(scanner.client, 'list_objects', side_effect=pages):
                    # Start memory tracking
                    tracemalloc.start()
                    
                    count = 0
                    async for obj in scanner.scan_objects():
                        count += 1
                    
                    current, peak = tracemalloc.get_traced_memory()
                    tracemalloc.stop()
                    
                    assert count == 10000
                    # Peak memory should be reasonable (less than 100MB for 10000 objects)
                    # Each object is roughly 200 bytes, so 10000 objects = ~2MB
                    # Allow generous margin for Python overhead
                    assert peak < 100 * 1024 * 1024, f"Peak memory: {peak / 1024 / 1024:.2f}MB"


class TestPerformanceExport:
    """Performance tests for export functionality"""
    
    @pytest.mark.asyncio
    async def test_excel_export_performance_1000_objects(self, temp_dir):
        """Test Excel export performance with 1000 objects"""
        exporter = ExcelExporterImpl(
            base_filename=os.path.join(temp_dir, 'test_export'),
            max_rows_per_sheet=1000000
        )
        
        # Generate 1000 objects
        objects = []
        for i in range(1000):
            objects.append(S3Object(
                key=f'file_{i}.txt',
                bucket='test-bucket',
                path=f'file_{i}.txt',
                last_modified=datetime.now(),
                size=1024,
                etag=f'etag-{i}'
            ))
        
        start_time = time.time()
        
        await exporter.open()
        await exporter.write(objects)
        files_saved = await exporter.close()
        
        elapsed_time = time.time() - start_time
        
        assert len(files_saved) == 1
        assert os.path.exists(files_saved[0])
        # Should complete in reasonable time
        assert elapsed_time < 5, f"Export took {elapsed_time:.2f}s, expected < 5s"
    
    @pytest.mark.asyncio
    async def test_excel_export_performance_10000_objects(self, temp_dir):
        """Test Excel export performance with 10000 objects"""
        exporter = ExcelExporterImpl(
            base_filename=os.path.join(temp_dir, 'test_export'),
            max_rows_per_sheet=1000000
        )
        
        # Generate 10000 objects
        objects = []
        for i in range(10000):
            objects.append(S3Object(
                key=f'file_{i}.txt',
                bucket='test-bucket',
                path=f'file_{i}.txt',
                last_modified=datetime.now(),
                size=1024,
                etag=f'etag-{i}'
            ))
        
        start_time = time.time()
        
        await exporter.open()
        await exporter.write(objects)
        files_saved = await exporter.close()
        
        elapsed_time = time.time() - start_time
        
        assert len(files_saved) == 1
        assert os.path.exists(files_saved[0])
        # Should complete in reasonable time
        assert elapsed_time < 10, f"Export took {elapsed_time:.2f}s, expected < 10s"
    
    @pytest.mark.asyncio
    async def test_excel_export_file_splitting(self, temp_dir):
        """Test Excel export with file splitting for large datasets"""
        exporter = ExcelExporterImpl(
            base_filename=os.path.join(temp_dir, 'test_export'),
            max_rows_per_sheet=1000  # Small batch size for testing
        )
        
        # Generate 3500 objects (should create 4 files)
        objects = []
        for i in range(3500):
            objects.append(S3Object(
                key=f'file_{i}.txt',
                bucket='test-bucket',
                path=f'file_{i}.txt',
                last_modified=datetime.now(),
                size=1024,
                etag=f'etag-{i}'
            ))
        
        await exporter.open()
        await exporter.write(objects)
        files_saved = await exporter.close()
        
        # Should have created at least 1 file
        assert len(files_saved) >= 1
        
        # Verify all files exist
        for file in files_saved:
            assert os.path.exists(file)
            assert file.endswith('.xlsx')


class TestPerformanceThreadPool:
    """Performance tests for thread pool"""
    
    @pytest.mark.asyncio
    async def test_thread_pool_concurrent_tasks(self):
        """Test thread pool with concurrent tasks"""
        from util.thread_pool import ThreadPoolImpl, ThreadPoolOptions
        
        options = ThreadPoolOptions(core_threads=4, max_threads=8)
        pool = ThreadPoolImpl(options)
        
        async def slow_task(n):
            await asyncio.sleep(0.01)
            return n * 2
        
        start_time = time.time()
        
        # Run 100 tasks concurrently
        tasks = [pool.submit(lambda n=i: slow_task(n)) for i in range(100)]
        results = await asyncio.gather(*tasks)
        
        elapsed_time = time.time() - start_time
        
        assert len(results) == 100
        assert results == [i * 2 for i in range(100)]
        # Concurrent execution should be faster than sequential
        # Sequential would take ~1 second (100 * 0.01s)
        assert elapsed_time < 0.5, f"Concurrent execution took {elapsed_time:.2f}s, expected < 0.5s"
    
    @pytest.mark.asyncio
    async def test_thread_pool_memory_efficiency(self):
        """Test thread pool memory efficiency"""
        from util.thread_pool import ThreadPoolImpl, ThreadPoolOptions
        
        options = ThreadPoolOptions(core_threads=2, max_threads=4)
        pool = ThreadPoolImpl(options)
        
        async def small_task(n):
            await asyncio.sleep(0.001)
            return n
        
        tracemalloc.start()
        
        # Run 1000 tasks
        tasks = [pool.submit(lambda n=i: small_task(n)) for i in range(1000)]
        results = await asyncio.gather(*tasks)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        assert len(results) == 1000
        # Should be memory efficient
        assert peak < 50 * 1024 * 1024, f"Peak memory: {peak / 1024 / 1024:.2f}MB"


class TestPerformanceLargeScale:
    """Large scale performance tests"""
    
    @pytest.mark.asyncio
    async def test_scan_100000_objects(self):
        """Test scanning 100000 objects (simulated)"""
        config = SystemConfig(
            scanner=ScannerConfig(max_keys_per_request=1000),
            exporter=ExporterConfig(type='excel'),
            thread_pool=ThreadPoolConfig(),
            s3=S3Config(
                endpoint='http://localhost:9000',
                region='us-east-1',
                access_key_id='test-key',
                secret_access_key='test-secret',
                bucket_name='test-bucket'
            ),
            excel=ExcelConfig()
        )
        
        scanner = S3ScannerImpl(config.s3, config.scanner)
        
        # Generate 100000 mock objects
        mock_objects = []
        for i in range(100000):
            mock_objects.append({
                'Key': f'folder/file_{i:05d}.txt',
                'LastModified': datetime.now(),
                'Size': 1024,
                'ETag': f'etag-{i}'
            })
        
        with patch.object(scanner.client, 'connect', return_value=True):
            with patch.object(scanner.client, 'is_connected', return_value=True):
                with patch.object(scanner.client, 'list_objects', return_value={
                    'KeyCount': 100000,
                    'Contents': mock_objects,
                    'IsTruncated': False
                }):
                    start_time = time.time()
                    
                    count = 0
                    async for obj in scanner.scan_objects():
                        count += 1
                    
                    elapsed_time = time.time() - start_time
                    
                    assert count == 100000
                    # Should complete in reasonable time
                    assert elapsed_time < 60, f"Scan took {elapsed_time:.2f}s, expected < 60s"
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_1gb(self):
        """Test that memory usage stays under 1GB for large datasets"""
        config = SystemConfig(
            scanner=ScannerConfig(max_keys_per_request=1000),
            exporter=ExporterConfig(type='excel'),
            thread_pool=ThreadPoolConfig(),
            s3=S3Config(
                endpoint='http://localhost:9000',
                region='us-east-1',
                access_key_id='test-key',
                secret_access_key='test-secret',
                bucket_name='test-bucket'
            ),
            excel=ExcelConfig()
        )
        
        scanner = S3ScannerImpl(config.s3, config.scanner)
        
        # Generate 50000 mock objects
        mock_objects = []
        for i in range(50000):
            mock_objects.append({
                'Key': f'folder/file_{i:05d}.txt',
                'LastModified': datetime.now(),
                'Size': 1024,
                'ETag': f'etag-{i}'
            })
        
        with patch.object(scanner.client, 'connect', return_value=True):
            with patch.object(scanner.client, 'is_connected', return_value=True):
                with patch.object(scanner.client, 'list_objects', return_value={
                    'KeyCount': 50000,
                    'Contents': mock_objects,
                    'IsTruncated': False
                }):
                    tracemalloc.start()
                    
                    count = 0
                    async for obj in scanner.scan_objects():
                        count += 1
                    
                    current, peak = tracemalloc.get_traced_memory()
                    tracemalloc.stop()
                    
                    assert count == 50000
                    # Should stay well under 1GB
                    assert peak < 1 * 1024 * 1024 * 1024, f"Peak memory: {peak / 1024 / 1024 / 1024:.2f}GB"

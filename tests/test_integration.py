"""Integration tests for S3 Bucket Scanner"""
import os
import pytest
import asyncio
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock, call
from pathlib import Path

from config.config_manager import ConfigManagerImpl
from scanner.s3_scanner import S3Credentials
from scanner.s3_scanner_impl import S3ScannerImpl
from exporter.excel_exporter import ExcelExporterImpl
from exporter.database_exporter import DatabaseExporterImpl
from model.config import SystemConfig, ScannerConfig, ExporterConfig, ThreadPoolConfig, S3Config, ExcelConfig, DatabaseConfig
from model.s3_object import S3Object


class TestIntegrationScanAndExport:
    """Integration tests for complete scan and export workflow"""
    
    @pytest.mark.asyncio
    async def test_scan_and_export_to_excel(self, temp_dir):
        """Test complete workflow: scan S3 and export to Excel"""
        # Create mock S3 objects
        mock_objects = []
        for i in range(10):
            mock_objects.append({
                'Key': f'folder/file_{i}.txt',
                'LastModified': datetime.now(),
                'Size': 1024 * (i + 1),
                'ETag': f'etag-{i}'
            })
        
        # Create config
        config = SystemConfig(
            scanner=ScannerConfig(max_keys_per_request=100),
            exporter=ExporterConfig(type='excel', output_dir=temp_dir),
            thread_pool=ThreadPoolConfig(core_threads=2, max_threads=4),
            s3=S3Config(
                endpoint='http://localhost:9000',
                region='us-east-1',
                access_key_id='test-key',
                secret_access_key='test-secret',
                bucket_name='test-bucket'
            ),
            excel=ExcelConfig(file_name='test_export', max_rows_per_sheet=1000)
        )
        
        # Create scanner
        scanner = S3ScannerImpl(config.s3, config.scanner)
        
        # Create exporter
        exporter = ExcelExporterImpl(
            base_filename=os.path.join(temp_dir, 'test_export'),
            max_rows_per_sheet=1000
        )
        
        # Mock S3 client
        with patch.object(scanner.client, 'connect', return_value=True):
            with patch.object(scanner.client, 'is_connected', return_value=True):
                with patch.object(scanner.client, 'list_objects', return_value={
                    'KeyCount': 10,
                    'Contents': mock_objects,
                    'IsTruncated': False
                }):
                    # Run scan and export
                    await exporter.open()
                    
                    batch = []
                    async for obj in scanner.scan_objects():
                        batch.append(obj)
                        
                        if len(batch) >= 100:  # batch size
                            await exporter.write(batch)
                            batch = []
                    
                    if batch:
                        await exporter.write(batch)
                    
                    files_saved = await exporter.close()
                    
                    # Verify results
                    assert len(files_saved) == 1
                    assert os.path.exists(files_saved[0])
                    assert scanner.get_progress().scanned_objects == 10
    
    @pytest.mark.asyncio
    async def test_scan_with_incremental(self, temp_dir):
        """Test incremental scan with resume capability"""
        # First scan - partial
        mock_objects_partial = [
            {'Key': 'file_1.txt', 'LastModified': datetime.now(), 'Size': 100, 'ETag': 'etag1'},
            {'Key': 'file_2.txt', 'LastModified': datetime.now(), 'Size': 200, 'ETag': 'etag2'}
        ]
        
        config = SystemConfig(
            scanner=ScannerConfig(max_keys_per_request=100),
            exporter=ExporterConfig(type='excel', output_dir=temp_dir),
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
        
        with patch.object(scanner.client, 'connect', return_value=True):
            with patch.object(scanner.client, 'is_connected', return_value=True):
                with patch.object(scanner.client, 'list_objects', return_value={
                    'KeyCount': 2,
                    'Contents': mock_objects_partial,
                    'IsTruncated': False
                }):
                    await scanner.connect('test-bucket', S3Credentials(
                        access_key_id='test-key',
                        secret_access_key='test-secret',
                        endpoint='http://localhost:9000',
                        region='us-east-1'
                    ))
                    
                    objects = []
                    async for obj in scanner.scan_objects():
                        objects.append(obj)
                    
                    # Save last key for resume
                    last_key = scanner.get_last_key()
                    progress = scanner.get_progress()
                    
                    assert len(objects) == 2
                    assert last_key == 'file_2.txt'
                    assert progress.scanned_objects == 2
        
        # Resume scan
        mock_objects_remaining = [
            {'Key': 'file_3.txt', 'LastModified': datetime.now(), 'Size': 300, 'ETag': 'etag3'},
            {'Key': 'file_4.txt', 'LastModified': datetime.now(), 'Size': 400, 'ETag': 'etag4'}
        ]
        
        scanner2 = S3ScannerImpl(config.s3, config.scanner)
        scanner2.set_last_key(last_key)
        
        with patch.object(scanner2.client, 'connect', return_value=True):
            with patch.object(scanner2.client, 'is_connected', return_value=True):
                with patch.object(scanner2.client, 'list_objects', return_value={
                    'KeyCount': 2,
                    'Contents': mock_objects_remaining,
                    'IsTruncated': False
                }):
                    objects = []
                    async for obj in scanner2.scan_objects():
                        objects.append(obj)
                    
                    assert len(objects) == 2
                    assert scanner2.get_progress().scanned_objects == 2
    
    @pytest.mark.asyncio
    async def test_scan_with_error_handling(self, temp_dir):
        """Test scan with error handling and retry"""
        config = SystemConfig(
            scanner=ScannerConfig(max_keys_per_request=100, max_retries=2, retry_delay=100),
            exporter=ExporterConfig(type='excel', output_dir=temp_dir),
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
        
        with patch.object(scanner.client, 'connect', return_value=True):
            with patch.object(scanner.client, 'is_connected', return_value=True):
                with patch.object(scanner.client, 'list_objects', side_effect=[
                    Exception('S3 Error'),
                    {'KeyCount': 1, 'Contents': [{'Key': 'file.txt', 'LastModified': datetime.now(), 'Size': 100, 'ETag': 'etag'}], 'IsTruncated': False}
                ]):
                    await scanner.connect('test-bucket', S3Credentials(
                        access_key_id='test-key',
                        secret_access_key='test-secret',
                        endpoint='http://localhost:9000',
                        region='us-east-1'
                    ))
                    
                    objects = []
                    async for obj in scanner.scan_objects():
                        objects.append(obj)
                    
                    assert len(objects) == 1
                    assert scanner.get_progress().errors == 1
    
    @pytest.mark.asyncio
    async def test_pause_and_resume_scan(self, temp_dir):
        """Test pausing and resuming scan"""
        config = SystemConfig(
            scanner=ScannerConfig(max_keys_per_request=100),
            exporter=ExporterConfig(type='excel', output_dir=temp_dir),
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
        
        with patch.object(scanner.client, 'connect', return_value=True):
            with patch.object(scanner.client, 'is_connected', return_value=True):
                # Simulate paused state
                scanner.pause()
                
                # Should not raise error when paused
                assert scanner._paused == True
                
                # Resume
                scanner.resume()
                assert scanner._paused == False
    
    @pytest.mark.asyncio
    async def test_stop_scan(self, temp_dir):
        """Test stopping scan"""
        config = SystemConfig(
            scanner=ScannerConfig(max_keys_per_request=100),
            exporter=ExporterConfig(type='excel', output_dir=temp_dir),
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
        
        with patch.object(scanner.client, 'connect', return_value=True):
            with patch.object(scanner.client, 'is_connected', return_value=True):
                # Stop scan
                scanner.stop()
                
                assert scanner._stopped == True
                
                # Resume should not clear stopped
                scanner.resume()
                assert scanner._stopped == True
    
    @pytest.mark.asyncio
    async def test_large_batch_export(self, temp_dir):
        """Test exporting large batch of objects"""
        config = SystemConfig(
            scanner=ScannerConfig(max_keys_per_request=1000),
            exporter=ExporterConfig(type='excel', output_dir=temp_dir),
            thread_pool=ThreadPoolConfig(),
            s3=S3Config(
                endpoint='http://localhost:9000',
                region='us-east-1',
                access_key_id='test-key',
                secret_access_key='test-secret',
                bucket_name='test-bucket'
            ),
            excel=ExcelConfig(file_name='large_export', max_rows_per_sheet=5)
        )
        
        scanner = S3ScannerImpl(config.s3, config.scanner)
        exporter = ExcelExporterImpl(
            base_filename=os.path.join(temp_dir, 'large_export'),
            max_rows_per_sheet=5
        )
        
        # Create 15 mock objects
        mock_objects = []
        for i in range(15):
            mock_objects.append({
                'Key': f'file_{i}.txt',
                'LastModified': datetime.now(),
                'Size': 1024,
                'ETag': f'etag-{i}'
            })
        
        with patch.object(scanner.client, 'connect', return_value=True):
            with patch.object(scanner.client, 'is_connected', return_value=True):
                with patch.object(scanner.client, 'list_objects', return_value={
                    'KeyCount': 15,
                    'Contents': mock_objects,
                    'IsTruncated': False
                }):
                    await exporter.open()
                    
                    batch = []
                    async for obj in scanner.scan_objects():
                        batch.append(obj)
                        
                        if len(batch) >= 100:
                            await exporter.write(batch)
                            batch = []
                    
                    if batch:
                        await exporter.write(batch)
                    
                    files_saved = await exporter.close()
                    
                    # Should have created at least 1 file
                    assert len(files_saved) >= 1
                    for file in files_saved:
                        assert os.path.exists(file)


class TestIntegrationDatabaseExport:
    """Integration tests for database export"""
    
    @pytest.mark.asyncio
    async def test_scan_and_export_to_database(self, temp_dir):
        """Test complete workflow: scan S3 and export to database"""
        config = SystemConfig(
            scanner=ScannerConfig(max_keys_per_request=100),
            exporter=ExporterConfig(type='database', output_dir=temp_dir),
            thread_pool=ThreadPoolConfig(),
            s3=S3Config(
                endpoint='http://localhost:9000',
                region='us-east-1',
                access_key_id='test-key',
                secret_access_key='test-secret',
                bucket_name='test-bucket'
            ),
            database=DatabaseConfig(
                type='mysql',
                host='localhost',
                port=3306,
                database='test_db',
                username='test_user',
                password='test_pass',
                table_name='s3_objects',
                batch_size=1000
            )
        )
        
        scanner = S3ScannerImpl(config.s3, config.scanner)
        
        with patch('exporter.database_exporter.create_database_connector') as mock_create:
            mock_connector = MagicMock()
            mock_create.return_value = mock_connector
            mock_connector.connect = AsyncMock()
            mock_connector.create_table_if_not_exists = AsyncMock()
            mock_connector.begin_transaction = AsyncMock()
            mock_connector.execute = AsyncMock()
            mock_connector.commit = AsyncMock()
            mock_connector.disconnect = AsyncMock()
            
            exporter = DatabaseExporterImpl(config=config.database)
            
            mock_objects = [
                {'Key': 'file1.txt', 'LastModified': datetime.now(), 'Size': 100, 'ETag': 'etag1'},
                {'Key': 'file2.txt', 'LastModified': datetime.now(), 'Size': 200, 'ETag': 'etag2'}
            ]
            
            with patch.object(scanner.client, 'connect', return_value=True):
                with patch.object(scanner.client, 'is_connected', return_value=True):
                    with patch.object(scanner.client, 'list_objects', return_value={
                        'KeyCount': 2,
                        'Contents': mock_objects,
                        'IsTruncated': False
                    }):
                        await exporter.open()
                        
                        batch = []
                        async for obj in scanner.scan_objects():
                            batch.append(obj)
                            
                            if len(batch) >= 100:
                                await exporter.write(batch)
                                batch = []
                        
                        if batch:
                            await exporter.write(batch)
                        
                        rows_written = await exporter.close()
                        
                        assert rows_written == 2
                        mock_connector.disconnect.assert_called_once()

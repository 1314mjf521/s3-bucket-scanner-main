"""Tests for S3 scanner"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from scanner.s3_scanner import S3Credentials
from scanner.s3_scanner_impl import S3ScannerImpl
from model.config import S3Config, ScannerConfig
from model.s3_object import S3Object, ScanProgress


class TestS3ScannerImpl:
    """Tests for S3ScannerImpl"""
    
    def test_scanner_initialization(self):
        """Test S3ScannerImpl initialization"""
        s3_config = S3Config(
            endpoint='http://localhost:9000',
            region='us-east-1',
            access_key_id='test-key',
            secret_access_key='test-secret',
            bucket_name='test-bucket'
        )
        scanner_config = ScannerConfig(
            max_keys_per_request=100,
            max_retries=3,
            retry_delay=1000
        )
        
        scanner = S3ScannerImpl(s3_config, scanner_config)
        
        assert scanner.s3_config == s3_config
        assert scanner.scanner_config == scanner_config
        assert scanner._paused == False
        assert scanner._stopped == False
        assert scanner._last_key is None
    
    def test_get_progress_initial(self):
        """Test getting initial progress"""
        s3_config = S3Config(
            endpoint='http://localhost:9000',
            region='us-east-1',
            access_key_id='test-key',
            secret_access_key='test-secret',
            bucket_name='test-bucket'
        )
        scanner_config = ScannerConfig()
        scanner = S3ScannerImpl(s3_config, scanner_config)
        
        progress = scanner.get_progress()
        
        assert progress.total_objects == 0
        assert progress.scanned_objects == 0
        assert progress.errors == 0
        assert progress.start_time is not None
    
    def test_pause_and_resume(self):
        """Test pausing and resuming scanner"""
        s3_config = S3Config(
            endpoint='http://localhost:9000',
            region='us-east-1',
            access_key_id='test-key',
            secret_access_key='test-secret',
            bucket_name='test-bucket'
        )
        scanner_config = ScannerConfig()
        scanner = S3ScannerImpl(s3_config, scanner_config)
        
        assert scanner._paused == False
        
        scanner.pause()
        assert scanner._paused == True
        
        scanner.resume()
        assert scanner._paused == False
    
    def test_stop(self):
        """Test stopping scanner"""
        s3_config = S3Config(
            endpoint='http://localhost:9000',
            region='us-east-1',
            access_key_id='test-key',
            secret_access_key='test-secret',
            bucket_name='test-bucket'
        )
        scanner_config = ScannerConfig()
        scanner = S3ScannerImpl(s3_config, scanner_config)
        
        assert scanner._stopped == False
        
        scanner.stop()
        assert scanner._stopped == True
    
    def test_get_last_key(self):
        """Test getting last scanned key"""
        s3_config = S3Config(
            endpoint='http://localhost:9000',
            region='us-east-1',
            access_key_id='test-key',
            secret_access_key='test-secret',
            bucket_name='test-bucket'
        )
        scanner_config = ScannerConfig()
        scanner = S3ScannerImpl(s3_config, scanner_config)
        
        assert scanner.get_last_key() is None
        
        scanner.set_last_key('test/file.txt')
        assert scanner.get_last_key() == 'test/file.txt'
    
    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful S3 connection"""
        s3_config = S3Config(
            endpoint='http://localhost:9000',
            region='us-east-1',
            access_key_id='test-key',
            secret_access_key='test-secret',
            bucket_name='test-bucket'
        )
        scanner_config = ScannerConfig()
        scanner = S3ScannerImpl(s3_config, scanner_config)
        
        credentials = S3Credentials(
            access_key_id='test-key',
            secret_access_key='test-secret',
            endpoint='http://localhost:9000',
            region='us-east-1'
        )
        
        with patch.object(scanner.client, 'connect', return_value=True):
            with patch.object(scanner.client, 'get_bucket_region', return_value='us-east-1'):
                await scanner.connect('test-bucket', credentials)
                
                assert scanner.s3_config.bucket_name == 'test-bucket'
    
    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test S3 connection failure"""
        s3_config = S3Config(
            endpoint='http://localhost:9000',
            region='us-east-1',
            access_key_id='test-key',
            secret_access_key='test-secret',
            bucket_name='test-bucket'
        )
        scanner_config = ScannerConfig()
        scanner = S3ScannerImpl(s3_config, scanner_config)
        
        credentials = S3Credentials(
            access_key_id='test-key',
            secret_access_key='test-secret',
            endpoint='http://localhost:9000',
            region='us-east-1'
        )
        
        with patch.object(scanner.client, 'connect', return_value=False):
            with pytest.raises(ConnectionError):
                await scanner.connect('test-bucket', credentials)
    
    @pytest.mark.asyncio
    async def test_scan_objects_empty_bucket(self):
        """Test scanning an empty bucket"""
        s3_config = S3Config(
            endpoint='http://localhost:9000',
            region='us-east-1',
            access_key_id='test-key',
            secret_access_key='test-secret',
            bucket_name='test-bucket'
        )
        scanner_config = ScannerConfig(max_keys_per_request=100)
        scanner = S3ScannerImpl(s3_config, scanner_config)
        
        with patch.object(scanner.client, 'connect', return_value=True):
            with patch.object(scanner.client, 'is_connected', return_value=True):
                with patch.object(scanner.client, 'list_objects', return_value={
                    'KeyCount': 0,
                    'Contents': [],
                    'IsTruncated': False
                }):
                    objects = []
                    async for obj in scanner.scan_objects():
                        objects.append(obj)
                    
                    assert len(objects) == 0
                    assert scanner.get_progress().scanned_objects == 0
    
    @pytest.mark.asyncio
    async def test_scan_objects_with_objects(self):
        """Test scanning bucket with objects"""
        s3_config = S3Config(
            endpoint='http://localhost:9000',
            region='us-east-1',
            access_key_id='test-key',
            secret_access_key='test-secret',
            bucket_name='test-bucket'
        )
        scanner_config = ScannerConfig(max_keys_per_request=100)
        scanner = S3ScannerImpl(s3_config, scanner_config)
        
        mock_objects = [
            {'Key': 'file1.txt', 'LastModified': datetime.now(), 'Size': 100, 'ETag': 'etag1'},
            {'Key': 'file2.txt', 'LastModified': datetime.now(), 'Size': 200, 'ETag': 'etag2'},
            {'Key': 'file3.txt', 'LastModified': datetime.now(), 'Size': 300, 'ETag': 'etag3'}
        ]
        
        with patch.object(scanner.client, 'connect', return_value=True):
            with patch.object(scanner.client, 'is_connected', return_value=True):
                with patch.object(scanner.client, 'list_objects', return_value={
                    'KeyCount': 3,
                    'Contents': mock_objects,
                    'IsTruncated': False
                }):
                    objects = []
                    async for obj in scanner.scan_objects():
                        objects.append(obj)
                    
                    assert len(objects) == 3
                    assert objects[0].key == 'file1.txt'
                    assert objects[1].key == 'file2.txt'
                    assert objects[2].key == 'file3.txt'
                    assert scanner.get_progress().scanned_objects == 3
    
    @pytest.mark.asyncio
    async def test_scan_objects_pagination(self):
        """Test scanning with pagination (truncated response)"""
        s3_config = S3Config(
            endpoint='http://localhost:9000',
            region='us-east-1',
            access_key_id='test-key',
            secret_access_key='test-secret',
            bucket_name='test-bucket'
        )
        scanner_config = ScannerConfig(max_keys_per_request=2)
        scanner = S3ScannerImpl(s3_config, scanner_config)
        
        # First page
        page1_response = {
            'KeyCount': 2,
            'Contents': [
                {'Key': 'file1.txt', 'LastModified': datetime.now(), 'Size': 100, 'ETag': 'etag1'},
                {'Key': 'file2.txt', 'LastModified': datetime.now(), 'Size': 200, 'ETag': 'etag2'}
            ],
            'IsTruncated': True,
            'NextContinuationToken': 'token1'
        }
        
        # Second page
        page2_response = {
            'KeyCount': 1,
            'Contents': [
                {'Key': 'file3.txt', 'LastModified': datetime.now(), 'Size': 300, 'ETag': 'etag3'}
            ],
            'IsTruncated': False
        }
        
        with patch.object(scanner.client, 'connect', return_value=True):
            with patch.object(scanner.client, 'is_connected', return_value=True):
                with patch.object(scanner.client, 'list_objects', side_effect=[page1_response, page2_response]):
                    objects = []
                    async for obj in scanner.scan_objects():
                        objects.append(obj)
                    
                    assert len(objects) == 3
                    assert scanner.get_progress().scanned_objects == 3
    
    @pytest.mark.asyncio
    async def test_scan_objects_incremental(self):
        """Test incremental scanning with last_key"""
        s3_config = S3Config(
            endpoint='http://localhost:9000',
            region='us-east-1',
            access_key_id='test-key',
            secret_access_key='test-secret',
            bucket_name='test-bucket'
        )
        scanner_config = ScannerConfig(max_keys_per_request=100)
        scanner = S3ScannerImpl(s3_config, scanner_config)
        
        # Set last key for incremental scan
        scanner.set_last_key('file2.txt')
        
        mock_objects = [
            {'Key': 'file3.txt', 'LastModified': datetime.now(), 'Size': 300, 'ETag': 'etag3'},
            {'Key': 'file4.txt', 'LastModified': datetime.now(), 'Size': 400, 'ETag': 'etag4'}
        ]
        
        with patch.object(scanner.client, 'connect', return_value=True):
            with patch.object(scanner.client, 'is_connected', return_value=True):
                with patch.object(scanner.client, 'list_objects', return_value={
                    'KeyCount': 2,
                    'Contents': mock_objects,
                    'IsTruncated': False
                }):
                    objects = []
                    async for obj in scanner.scan_objects():
                        objects.append(obj)
                    
                    assert len(objects) == 2
                    assert scanner.get_progress().scanned_objects == 2
                    assert scanner.get_last_key() == 'file4.txt'
    
    @pytest.mark.asyncio
    async def test_scan_objects_error_handling(self):
        """Test scanning with error and retry"""
        s3_config = S3Config(
            endpoint='http://localhost:9000',
            region='us-east-1',
            access_key_id='test-key',
            secret_access_key='test-secret',
            bucket_name='test-bucket'
        )
        scanner_config = ScannerConfig(max_keys_per_request=100, max_retries=2, retry_delay=100)
        scanner = S3ScannerImpl(s3_config, scanner_config)
        
        with patch.object(scanner.client, 'connect', return_value=True):
            with patch.object(scanner.client, 'is_connected', return_value=True):
                with patch.object(scanner.client, 'list_objects', side_effect=[
                    Exception('S3 Error'),
                    {'KeyCount': 1, 'Contents': [{'Key': 'file1.txt', 'LastModified': datetime.now(), 'Size': 100, 'ETag': 'etag1'}], 'IsTruncated': False}
                ]):
                    objects = []
                    async for obj in scanner.scan_objects():
                        objects.append(obj)
                    
                    assert len(objects) == 1
                    assert scanner.get_progress().errors == 1
    
    @pytest.mark.asyncio
    async def test_scan_objects_max_retries_exceeded(self):
        """Test scanning with max retries exceeded"""
        s3_config = S3Config(
            endpoint='http://localhost:9000',
            region='us-east-1',
            access_key_id='test-key',
            secret_access_key='test-secret',
            bucket_name='test-bucket'
        )
        scanner_config = ScannerConfig(max_keys_per_request=100, max_retries=2, retry_delay=100)
        scanner = S3ScannerImpl(s3_config, scanner_config)
        
        with patch.object(scanner.client, 'connect', return_value=True):
            with patch.object(scanner.client, 'is_connected', return_value=True):
                with patch.object(scanner.client, 'list_objects', side_effect=Exception('S3 Error')):
                    with pytest.raises(RuntimeError, match='Scan failed after 2 retries'):
                        objects = []
                        async for obj in scanner.scan_objects():
                            objects.append(obj)
    
    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnecting scanner"""
        s3_config = S3Config(
            endpoint='http://localhost:9000',
            region='us-east-1',
            access_key_id='test-key',
            secret_access_key='test-secret',
            bucket_name='test-bucket'
        )
        scanner_config = ScannerConfig()
        scanner = S3ScannerImpl(s3_config, scanner_config)
        
        with patch.object(scanner.client, 'connect', return_value=True):
            await scanner.connect('test-bucket', S3Credentials(
                access_key_id='test-key',
                secret_access_key='test-secret',
                endpoint='http://localhost:9000',
                region='us-east-1'
            ))
            
            # The connect method doesn't actually call client.connect()
            # It just sets the bucket name, so we need to mock is_connected
            with patch.object(scanner.client, 'is_connected', return_value=True):
                assert scanner.client.is_connected() == True
            
            await scanner.disconnect()
            assert scanner.client.is_connected() == False
            assert scanner._paused == False
            assert scanner._stopped == False

"""Tests for data models"""
import pytest
from datetime import datetime
from model.s3_object import S3Object, ScanProgress
from model.config import (
    S3Config, ScannerConfig, ExporterConfig, DatabaseConfig,
    ExcelConfig, ThreadPoolConfig, SystemConfig, ConfigValidationError
)


class TestS3Object:
    """Tests for S3Object data model"""
    
    def test_s3_object_creation(self):
        """Test creating an S3Object"""
        obj = S3Object(
            key='test/file.txt',
            bucket='test-bucket',
            path='test/file.txt',
            last_modified=datetime.now(),
            size=1024,
            etag='test-etag'
        )
        assert obj.key == 'test/file.txt'
        assert obj.bucket == 'test-bucket'
        assert obj.path == 'test/file.txt'
        assert obj.size == 1024
        assert obj.etag == 'test-etag'
    
    def test_s3_object_default_values(self):
        """Test S3Object with default values"""
        obj = S3Object(
            key='test.txt',
            bucket='bucket',
            path='test.txt',
            last_modified=datetime.now(),
            size=0,
            etag=''
        )
        assert obj.size == 0
        assert obj.etag == ''


class TestScanProgress:
    """Tests for ScanProgress data model"""
    
    def test_scan_progress_creation(self):
        """Test creating a ScanProgress"""
        start_time = datetime.now()
        progress = ScanProgress(
            total_objects=1000,
            scanned_objects=500,
            start_time=start_time
        )
        assert progress.total_objects == 1000
        assert progress.scanned_objects == 500
        assert progress.errors == 0
        assert progress.start_time == start_time
    
    def test_scan_progress_default_values(self):
        """Test ScanProgress with default values"""
        progress = ScanProgress(
            total_objects=0,
            scanned_objects=0
        )
        assert progress.total_objects == 0
        assert progress.scanned_objects == 0
        assert progress.errors == 0
        assert progress.current_prefix is None


class TestS3Config:
    """Tests for S3Config"""
    
    def test_s3_config_valid(self):
        """Test valid S3Config"""
        config = S3Config(
            endpoint='http://localhost:9000',
            region='us-east-1',
            access_key_id='test-key',
            secret_access_key='test-secret',
            bucket_name='test-bucket',
            use_ssl=False
        )
        config.validate()
    
    def test_s3_config_missing_endpoint(self):
        """Test S3Config validation with missing endpoint"""
        config = S3Config(
            endpoint=None,
            access_key_id='test-key',
            secret_access_key='test-secret',
            bucket_name='test-bucket'
        )
        with pytest.raises(ConfigValidationError):
            config.validate()
    
    def test_s3_config_missing_bucket(self):
        """Test S3Config validation with missing bucket name"""
        config = S3Config(
            endpoint='http://localhost:9000',
            access_key_id='test-key',
            secret_access_key='test-secret',
            bucket_name=''
        )
        with pytest.raises(ConfigValidationError):
            config.validate()
    
    def test_s3_config_with_prefix(self):
        """Test S3Config with optional prefix"""
        config = S3Config(
            endpoint='http://localhost:9000',
            access_key_id='test-key',
            secret_access_key='test-secret',
            bucket_name='test-bucket',
            prefix='/test/',
            use_ssl=True
        )
        config.validate()
        assert config.prefix == '/test/'


class TestScannerConfig:
    """Tests for ScannerConfig"""
    
    def test_scanner_config_valid(self):
        """Test valid ScannerConfig"""
        config = ScannerConfig(
            max_keys_per_request=1000,
            max_retries=3,
            retry_delay=1000,
            enable_incremental=False
        )
        config.validate()
    
    def test_scanner_config_invalid_max_keys(self):
        """Test ScannerConfig with invalid max_keys_per_request"""
        config = ScannerConfig(
            max_keys_per_request=0,
            max_retries=3,
            retry_delay=1000
        )
        with pytest.raises(ConfigValidationError):
            config.validate()
    
    def test_scanner_config_invalid_retry_delay(self):
        """Test ScannerConfig with negative retry delay"""
        config = ScannerConfig(
            max_keys_per_request=1000,
            max_retries=3,
            retry_delay=-100
        )
        with pytest.raises(ConfigValidationError):
            config.validate()


class TestExporterConfig:
    """Tests for ExporterConfig"""
    
    def test_exporter_config_valid_excel(self):
        """Test valid Excel ExporterConfig"""
        config = ExporterConfig(
            type='excel',
            output_dir='./output'
        )
        config.validate()
    
    def test_exporter_config_valid_database(self):
        """Test valid Database ExporterConfig"""
        config = ExporterConfig(
            type='database',
            output_dir='./output'
        )
        config.validate()
    
    def test_exporter_config_invalid_type(self):
        """Test ExporterConfig with invalid type"""
        config = ExporterConfig(
            type='invalid',
            output_dir='./output'
        )
        with pytest.raises(ConfigValidationError):
            config.validate()
    
    def test_exporter_config_missing_output_dir(self):
        """Test ExporterConfig with empty output_dir"""
        config = ExporterConfig(
            type='excel',
            output_dir=''
        )
        with pytest.raises(ConfigValidationError):
            config.validate()


class TestDatabaseConfig:
    """Tests for DatabaseConfig"""
    
    def test_database_config_valid_mysql(self):
        """Test valid MySQL DatabaseConfig"""
        config = DatabaseConfig(
            type='mysql',
            host='localhost',
            port=3306,
            database='test_db',
            username='test_user',
            password='test_pass',
            table_name='test_table',
            batch_size=1000
        )
        config.validate()
    
    def test_database_config_valid_postgresql(self):
        """Test valid PostgreSQL DatabaseConfig"""
        config = DatabaseConfig(
            type='postgresql',
            host='localhost',
            port=5432,
            database='test_db',
            username='test_user',
            password='test_pass',
            table_name='test_table'
        )
        config.validate()
    
    def test_database_config_invalid_type(self):
        """Test DatabaseConfig with invalid type"""
        config = DatabaseConfig(
            type='invalid',
            host='localhost',
            database='test_db',
            username='test_user',
            password='test_pass',
            table_name='test_table'
        )
        with pytest.raises(ConfigValidationError):
            config.validate()
    
    def test_database_config_missing_required_fields(self):
        """Test DatabaseConfig with missing required fields"""
        config = DatabaseConfig(
            type='mysql',
            host='',
            database='test_db',
            username='test_user',
            password='test_pass',
            table_name='test_table'
        )
        with pytest.raises(ConfigValidationError):
            config.validate()


class TestExcelConfig:
    """Tests for ExcelConfig"""
    
    def test_excel_config_valid(self):
        """Test valid ExcelConfig"""
        config = ExcelConfig(
            file_name='test_export',
            max_rows_per_sheet=1000000,
            split_file=True
        )
        config.validate()
    
    def test_excel_config_invalid_max_rows(self):
        """Test ExcelConfig with invalid max_rows_per_sheet"""
        config = ExcelConfig(
            file_name='test_export',
            max_rows_per_sheet=0,
            split_file=True
        )
        with pytest.raises(ConfigValidationError):
            config.validate()


class TestThreadPoolConfig:
    """Tests for ThreadPoolConfig"""
    
    def test_thread_pool_config_valid(self):
        """Test valid ThreadPoolConfig"""
        config = ThreadPoolConfig(
            core_threads=4,
            max_threads=10,
            queue_size=1000,
            keep_alive_time=60
        )
        config.validate()
    
    def test_thread_pool_config_invalid_max_threads(self):
        """Test ThreadPoolConfig with max_threads < core_threads"""
        config = ThreadPoolConfig(
            core_threads=10,
            max_threads=4,
            queue_size=1000
        )
        with pytest.raises(ConfigValidationError):
            config.validate()
    
    def test_thread_pool_config_invalid_queue_size(self):
        """Test ThreadPoolConfig with invalid queue_size"""
        config = ThreadPoolConfig(
            core_threads=4,
            max_threads=10,
            queue_size=0
        )
        with pytest.raises(ConfigValidationError):
            config.validate()


class TestSystemConfig:
    """Tests for SystemConfig"""
    
    def test_system_config_valid_excel(self):
        """Test valid SystemConfig with Excel exporter"""
        config = SystemConfig(
            scanner=ScannerConfig(),
            exporter=ExporterConfig(type='excel', output_dir='./output'),
            thread_pool=ThreadPoolConfig(),
            s3=S3Config(
                endpoint='http://localhost:9000',
                access_key_id='test-key',
                secret_access_key='test-secret',
                bucket_name='test-bucket'
            ),
            excel=ExcelConfig()
        )
        config.validate()
    
    def test_system_config_valid_database(self):
        """Test valid SystemConfig with Database exporter"""
        config = SystemConfig(
            scanner=ScannerConfig(),
            exporter=ExporterConfig(type='database', output_dir='./output'),
            thread_pool=ThreadPoolConfig(),
            s3=S3Config(
                endpoint='http://localhost:9000',
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
                table_name='test_table',
                batch_size=1000
            )
        )
        config.validate()
    
    def test_system_config_missing_excel_when_excel_exporter(self):
        """Test SystemConfig with Excel exporter but no excel config"""
        config = SystemConfig(
            scanner=ScannerConfig(),
            exporter=ExporterConfig(type='excel', output_dir='./output'),
            thread_pool=ThreadPoolConfig(),
            s3=S3Config(
                endpoint='http://localhost:9000',
                access_key_id='test-key',
                secret_access_key='test-secret',
                bucket_name='test-bucket'
            )
        )
        with pytest.raises(ConfigValidationError):
            config.validate()
    
    def test_system_config_missing_database_when_database_exporter(self):
        """Test SystemConfig with Database exporter but no database config"""
        config = SystemConfig(
            scanner=ScannerConfig(),
            exporter=ExporterConfig(type='database', output_dir='./output'),
            thread_pool=ThreadPoolConfig(),
            s3=S3Config(
                endpoint='http://localhost:9000',
                access_key_id='test-key',
                secret_access_key='test-secret',
                bucket_name='test-bucket'
            )
        )
        with pytest.raises(ConfigValidationError):
            config.validate()

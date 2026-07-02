"""Tests for configuration manager"""
import os
import pytest
import yaml
from unittest.mock import patch, MagicMock
from config.config_manager import ConfigManagerImpl, ConfigValidationError


class TestConfigManagerImpl:
    """Tests for ConfigManagerImpl"""
    
    def test_load_config_valid_yaml(self, test_config_yaml):
        """Test loading a valid YAML configuration"""
        manager = ConfigManagerImpl()
        config = manager.load_config(test_config_yaml)
        
        assert config.s3.endpoint == 'http://localhost:9000'
        assert config.s3.region == 'us-east-1'
        assert config.s3.access_key_id == 'test-access-key'
        assert config.s3.secret_access_key == 'test-secret-key'
        assert config.s3.bucket_name == 'test-bucket'
        assert config.s3.prefix == '/test/'
        assert config.s3.use_ssl == False
        
        assert config.scanner.max_keys_per_request == 100
        assert config.scanner.max_retries == 2
        assert config.scanner.retry_delay == 500
        
        assert config.exporter.type == 'excel'
        assert config.exporter.output_dir == './output'
        
        assert config.thread_pool.core_threads == 2
        assert config.thread_pool.max_threads == 4
        
        assert config.excel.file_name == 'test_export'
        assert config.excel.max_rows_per_sheet == 1000
    
    def test_load_config_missing_file(self):
        """Test loading a non-existent configuration file"""
        manager = ConfigManagerImpl()
        with pytest.raises(FileNotFoundError):
            manager.load_config('/nonexistent/path/config.yaml')
    
    def test_load_config_invalid_yaml(self, temp_dir):
        """Test loading an invalid YAML configuration"""
        invalid_yaml = os.path.join(temp_dir, 'invalid.yaml')
        with open(invalid_yaml, 'w') as f:
            f.write('invalid: yaml: content: [')
        
        manager = ConfigManagerImpl()
        with pytest.raises(Exception):
            manager.load_config(invalid_yaml)
    
    def test_get_scanner_config(self, test_config_yaml):
        """Test getting scanner config"""
        manager = ConfigManagerImpl()
        manager.load_config(test_config_yaml)
        
        scanner_config = manager.get_scanner_config()
        assert scanner_config.max_keys_per_request == 100
        assert scanner_config.max_retries == 2
    
    def test_get_exporter_config(self, test_config_yaml):
        """Test getting exporter config"""
        manager = ConfigManagerImpl()
        manager.load_config(test_config_yaml)
        
        exporter_config = manager.get_exporter_config()
        assert exporter_config.type == 'excel'
        assert exporter_config.output_dir == './output'
    
    def test_get_thread_pool_config(self, test_config_yaml):
        """Test getting thread pool config"""
        manager = ConfigManagerImpl()
        manager.load_config(test_config_yaml)
        
        pool_config = manager.get_thread_pool_config()
        assert pool_config.core_threads == 2
        assert pool_config.max_threads == 4
    
    def test_get_s3_config(self, test_config_yaml):
        """Test getting S3 config"""
        manager = ConfigManagerImpl()
        manager.load_config(test_config_yaml)
        
        s3_config = manager.get_s3_config()
        assert s3_config.bucket_name == 'test-bucket'
        assert s3_config.endpoint == 'http://localhost:9000'
    
    def test_get_database_config(self, test_config_yaml):
        """Test getting database config (should be None for Excel)"""
        manager = ConfigManagerImpl()
        manager.load_config(test_config_yaml)
        
        db_config = manager.get_database_config()
        assert db_config is None
    
    def test_get_excel_config(self, test_config_yaml):
        """Test getting Excel config"""
        manager = ConfigManagerImpl()
        manager.load_config(test_config_yaml)
        
        excel_config = manager.get_excel_config()
        assert excel_config.file_name == 'test_export'
        assert excel_config.split_file == True
    
    def test_load_config_with_database_exporter(self, temp_dir):
        """Test loading configuration with database exporter"""
        config_content = """
scanner:
  maxKeysPerRequest: 1000

exporter:
  type: database
  outputDir: ./output

threadPool:
  coreThreads: 4
  maxThreads: 10

s3:
  endpoint: http://localhost:9000
  region: us-east-1
  accessKeyId: test-key
  secretAccessKey: test-secret
  bucketName: test-bucket

database:
  type: mysql
  host: localhost
  port: 3306
  database: test_db
  username: test_user
  password: test_pass
  tableName: s3_objects
  batchSize: 1000
"""
        config_path = os.path.join(temp_dir, 'db_config.yaml')
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        manager = ConfigManagerImpl()
        config = manager.load_config(config_path)
        
        assert config.exporter.type == 'database'
        assert config.database is not None
        assert config.database.type == 'mysql'
        assert config.database.host == 'localhost'
        assert config.database.port == 3306
    
    def test_config_validation_failure(self, temp_dir):
        """Test configuration validation failure"""
        config_content = """
scanner:
  maxKeysPerRequest: 0

exporter:
  type: excel
  outputDir: ./output

threadPool:
  coreThreads: 4
  maxThreads: 10

s3:
  endpoint: http://localhost:9000
  region: us-east-1
  accessKeyId: test-key
  secretAccessKey: test-secret
  bucketName: test-bucket

excel:
  fileName: test
  maxRowsPerSheet: 1000
"""
        config_path = os.path.join(temp_dir, 'invalid_config.yaml')
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        manager = ConfigManagerImpl()
        with pytest.raises(ConfigValidationError):
            manager.load_config(config_path)

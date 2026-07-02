"""Tests for utility modules"""
import pytest
from util.plugin_loader import PluginLoader


class TestPluginLoader:
    """Tests for PluginLoader"""
    
    def test_initialization(self):
        """Test PluginLoader initialization"""
        loader = PluginLoader()
        assert loader.base_dir == '.'
        assert loader.loaded_plugins == {}
    
    def test_initialization_with_base_dir(self):
        """Test PluginLoader initialization with custom base_dir"""
        loader = PluginLoader(base_dir='/custom/path')
        assert loader.base_dir == '/custom/path'
    
    def test_load_plugin_with_params_excel(self):
        """Test loading Excel exporter plugin"""
        loader = PluginLoader()
        
        exporter = loader.load_plugin_with_params(
            'exporter.excel_exporter',
            'ExcelExporterImpl',
            base_filename='test',
            max_rows_per_sheet=1000
        )
        
        assert exporter is not None
        assert exporter.base_filename == 'test'
    
    def test_load_plugin_with_params_database(self):
        """Test loading Database exporter plugin"""
        loader = PluginLoader()
        
        from model.config import DatabaseConfig
        config = DatabaseConfig(
            type='mysql',
            host='localhost',
            port=3306,
            database='test_db',
            username='test_user',
            password='test_pass',
            table_name='test_table'
        )
        
        exporter = loader.load_plugin_with_params(
            'exporter.database_exporter',
            'DatabaseExporterImpl',
            config=config
        )
        
        assert exporter is not None
        assert exporter.table_name == 'test_table'
    
    def test_load_exporter_excel(self):
        """Test loading Excel exporter via load_exporter"""
        loader = PluginLoader()
        
        from model.config import SystemConfig, ScannerConfig, ExporterConfig, ThreadPoolConfig, S3Config, ExcelConfig
        
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
            excel=ExcelConfig(file_name='test', max_rows_per_sheet=1000)
        )
        
        exporter = loader.load_exporter('excel', config)
        
        assert exporter is not None
    
    def test_load_exporter_database(self):
        """Test loading Database exporter via load_exporter"""
        loader = PluginLoader()
        
        from model.config import SystemConfig, ScannerConfig, ExporterConfig, ThreadPoolConfig, S3Config, DatabaseConfig
        
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
                table_name='test_table'
            )
        )
        
        exporter = loader.load_exporter('database', config)
        
        assert exporter is not None
    
    def test_load_exporter_unknown_type(self):
        """Test loading exporter with unknown type"""
        loader = PluginLoader()
        
        from model.config import SystemConfig, ScannerConfig, ExporterConfig, ThreadPoolConfig, S3Config
        
        config = SystemConfig(
            scanner=ScannerConfig(),
            exporter=ExporterConfig(type='unknown', output_dir='./output'),
            thread_pool=ThreadPoolConfig(),
            s3=S3Config(
                endpoint='http://localhost:9000',
                access_key_id='test-key',
                secret_access_key='test-secret',
                bucket_name='test-bucket'
            )
        )
        
        exporter = loader.load_exporter('unknown', config)
        
        assert exporter is None
    
    def test_get_plugin(self):
        """Test getting loaded plugin"""
        loader = PluginLoader()
        
        loader.load_plugin_with_params(
            'exporter.excel_exporter',
            'ExcelExporterImpl',
            base_filename='test'
        )
        
        # Get the plugin by name
        plugin_name = 'exporter.excel_exporter.ExcelExporterImpl'
        plugin = loader.get_plugin(plugin_name)
        
        assert plugin is not None
    
    def test_get_all_plugins(self):
        """Test getting all loaded plugins"""
        loader = PluginLoader()
        
        loader.load_plugin_with_params(
            'exporter.excel_exporter',
            'ExcelExporterImpl',
            base_filename='test1'
        )
        
        loader.load_plugin_with_params(
            'exporter.excel_exporter',
            'ExcelExporterImpl',
            base_filename='test2'
        )
        
        plugins = loader.get_all_plugins()
        
        assert len(plugins) >= 1
    
    def test_clear_plugins(self):
        """Test clearing loaded plugins"""
        loader = PluginLoader()
        
        loader.load_plugin_with_params(
            'exporter.excel_exporter',
            'ExcelExporterImpl',
            base_filename='test'
        )
        
        loader.clear_plugins()
        
        assert len(loader.loaded_plugins) == 0
    
    def test_create_exporter_factory(self):
        """Test create_exporter factory function"""
        from util.plugin_loader import create_exporter
        from model.config import SystemConfig, ScannerConfig, ExporterConfig, ThreadPoolConfig, S3Config, ExcelConfig
        
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
            excel=ExcelConfig(file_name='test', max_rows_per_sheet=1000)
        )
        
        exporter = create_exporter('excel', config)
        
        assert exporter is not None

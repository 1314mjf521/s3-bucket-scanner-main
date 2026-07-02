"""Test configuration and fixtures"""
import pytest
import os
import tempfile
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def test_config_yaml():
    """Create a test configuration YAML file"""
    config_content = """
scanner:
  maxKeysPerRequest: 100
  maxRetries: 2
  retryDelay: 500
  enableIncremental: false

exporter:
  type: excel
  outputDir: ./output

threadPool:
  coreThreads: 2
  maxThreads: 4
  queueSize: 100
  keepAliveTime: 30

s3:
  endpoint: http://localhost:9000
  region: us-east-1
  accessKeyId: test-access-key
  secretAccessKey: test-secret-key
  bucketName: test-bucket
  prefix: /test/
  useSSL: false

excel:
  fileName: test_export
  maxRowsPerSheet: 1000
  splitFile: true
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def mock_s3_credentials():
    """Create mock S3 credentials for testing"""
    from scanner.s3_scanner import S3Credentials
    return S3Credentials(
        access_key_id='test-access-key',
        secret_access_key='test-secret-key',
        endpoint='http://localhost:9000',
        region='us-east-1',
        use_ssl=False
    )


@pytest.fixture
def mock_s3_object():
    """Create a mock S3 object"""
    from datetime import datetime
    from model.s3_object import S3Object
    return S3Object(
        key='test/file.txt',
        bucket='test-bucket',
        path='test/file.txt',
        last_modified=datetime.now(),
        size=1024,
        etag='test-etag'
    )


@pytest.fixture
def mock_s3_objects():
    """Create a list of mock S3 objects"""
    from datetime import datetime
    from model.s3_object import S3Object
    objects = []
    for i in range(10):
        objects.append(S3Object(
            key=f'test/file_{i}.txt',
            bucket='test-bucket',
            path=f'test/file_{i}.txt',
            last_modified=datetime.now(),
            size=1024 * (i + 1),
            etag=f'etag-{i}'
        ))
    return objects

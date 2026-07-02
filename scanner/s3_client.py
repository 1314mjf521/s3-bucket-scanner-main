"""S3客户端连接器"""
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from botocore.client import Config
from typing import Optional
from model.config import S3Config


class S3Client:
    """S3客户端连接器，处理凭证和连接配置"""
    
    def __init__(self, config: S3Config):
        """
        初始化S3客户端
        
        Args:
            config: S3配置对象
        """
        self.config = config
        self.client: Optional[boto3.client] = None
        self._retries = 0
        self._max_retries = 3  # 最大重试次数
        self._use_path_style = False  # 是否使用路径样式访问（兼容MinIO等）
        self._use_path_style_addressing = False  # 是否使用路径样式寻址
    
    def connect(self) -> bool:
        """
        连接到S3服务
        
        Returns:
            bool: 连接成功返回True，否则抛出异常
        """
        # 构建客户端配置
        client_config = Config(
            signature_version='s3v4',  # 使用S3 v4签名
            connect_timeout=30,
            read_timeout=30,
            retries={"max_attempts": 3}  # boto3最大重试次数
        )
        
        # 构建客户端参数
        client_params = {
            'config': client_config,
            'use_ssl': self.config.use_ssl
        }
        
        # 如果配置了endpoint_url，则使用自定义端点（兼容MinIO、阿里云OSS等）
        if self.config.endpoint:
            client_params['endpoint_url'] = self.config.endpoint
            # 对于自定义端点，使用路径样式访问
            self._use_path_style_addressing = True
            # 配置S3客户端使用路径样式寻址（深信服SCP需要）
            client_config.s3 = {'addressing_style': 'path'}
        
        # 如果提供了region，则设置（某些S3平台如深信服不需要region）
        if self.config.region:
            client_params['region_name'] = self.config.region
        
        # 如果提供了访问凭证，则使用
        if self.config.access_key_id and self.config.secret_access_key:
            client_params['aws_access_key_id'] = self.config.access_key_id
            client_params['aws_secret_access_key'] = self.config.secret_access_key
        
        # 创建S3客户端
        self.client = boto3.client('s3', **client_params)
        
        # 验证连接 - 尝试获取桶位置
        self.client.head_bucket(Bucket=self.config.bucket_name)
        self._retries = 0
        return True
    
    def disconnect(self) -> None:
        """断开S3连接"""
        self.client = None
        self._retries = 0
    
    def is_connected(self) -> bool:
        """
        检查是否已连接
        
        Returns:
            bool: 已连接返回True
        """
        return self.client is not None
    
    def list_objects(self, prefix: Optional[str] = None, marker: Optional[str] = None, max_keys: int = 1000):
        """
        列出S3对象（使用list_objects API和Marker分页）
        
        Args:
            prefix: 对象键前缀
            marker: 分页标记（作为Marker参数）
            max_keys: 最大返回对象数
            
        Returns:
            列表响应（包含单页对象）
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        params = {
            'Bucket': self.config.bucket_name,
            'MaxKeys': max_keys
        }
        
        if prefix:
            params['Prefix'] = prefix
        
        # 使用 Marker 进行分页（list_objects API 使用 Marker 参数）
        # 注意：Marker 是 list_objects 的参数，不是 StartAfter
        if marker:
            params['Marker'] = marker
        
        print(f"DEBUG: list_objects - marker: {marker}, Marker: {params.get('Marker')}, MaxKeys: {max_keys}")
        
        # 使用 list_objects API（而不是 list_objects_v2）以兼容深信服SCP
        try:
            response = self.client.list_objects(**params)
            return response
            
        except ClientError as e:
            error_msg = str(e)
            print(f"DEBUG: List objects failed. Error: {error_msg[:200]}")
            
            # 如果 Marker 参数导致 500 错误（深信服SCP的已知问题），尝试不使用 Marker
            # 这会导致重新扫描，但对于深信服SCP是必要的
            if '500' in error_msg or 'Internal Server Error' in error_msg:
                print("DEBUG: 500 error detected with Marker, trying without Marker parameter...")
                params.pop('Marker', None)
                try:
                    response = self.client.list_objects(**params)
                    return response
                except ClientError as e2:
                    raise RuntimeError(f"Failed to list objects: {str(e2)}")
            
            # 如果 Marker 参数不被支持，尝试使用 list_objects_v2 + StartAfter
            if 'Unknown parameter' in error_msg and 'Marker' in error_msg:
                print("DEBUG: Marker not supported, trying list_objects_v2 with StartAfter...")
                params.pop('Marker', None)
                if marker:
                    params['StartAfter'] = marker
                try:
                    response = self.client.list_objects_v2(**params)
                    return response
                except ClientError as e2:
                    raise RuntimeError(f"Failed to list objects: {str(e2)}")
            
            raise RuntimeError(f"Failed to list objects: {str(e)}")
    
    def get_bucket_region(self) -> str:
        """
        获取桶所在区域
        
        Returns:
            区域名称
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
        
        try:
            response = self.client.get_bucket_location(
                Bucket=self.config.bucket_name
            )
            location = response.get('LocationConstraint')
            # 对于us-east-1，LocationConstraint返回None
            return location if location else 'us-east-1'
        except ClientError as e:
            raise RuntimeError(f"Failed to get bucket location: {str(e)}")

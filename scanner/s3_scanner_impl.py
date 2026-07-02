"""S3对象扫描器实现"""
import asyncio
import json
import os
from typing import AsyncIterator, Optional
from datetime import datetime
from scanner.s3_scanner import S3Scanner
from scanner.s3_client import S3Client
from model.s3_object import S3Object, ScanProgress
from model.config import S3Config, ScannerConfig


class CheckpointManager:
    """断点管理器，用于持久化和恢复扫描进度"""
    
    def __init__(self, checkpoint_file: str = './.checkpoint.json'):
        self.checkpoint_file = checkpoint_file
    
    def load_checkpoint(self) -> Optional[str]:
        """加载断点（返回对象键作为断点）"""
        if not os.path.exists(self.checkpoint_file):
            return None
        
        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('last_key') or data.get('next_continuation_token')
        except Exception:
            return None
    
    def save_checkpoint(self, last_key: str) -> None:
        """保存断点（保存对象键）"""
        data = {
            'last_key': last_key,
            'timestamp': datetime.now().isoformat()
        }
        with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def clear_checkpoint(self) -> None:
        """清除断点"""
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)


class S3ScannerImpl(S3Scanner):
    """S3对象扫描器实现，支持分页和增量扫描"""
    
    def __init__(self, s3_config: S3Config, scanner_config: ScannerConfig):
        """
        初始化S3扫描器
        
        Args:
            s3_config: S3配置
            scanner_config: 扫描器配置
        """
        self.s3_config = s3_config
        self.scanner_config = scanner_config
        self.client = S3Client(s3_config)
        self.progress = ScanProgress(
            total_objects=0,
            scanned_objects=0,
            start_time=datetime.now()
        )
        self._paused = False
        self._stopped = False
        self._last_key: Optional[str] = None  # 用于增量扫描的断点
        self._current_marker: Optional[str] = None  # 当前分页标记
        self.checkpoint_manager = CheckpointManager()
    
    async def connect(self, bucket_name: str, credentials) -> None:
        """
        连接到S3桶
        
        Args:
            bucket_name: 桶名称
            credentials: 凭证对象（兼容S3Credentials或直接使用配置）
        """
        # 更新桶名称
        self.s3_config.bucket_name = bucket_name
        
        # 连接S3
        if not self.client.connect():
            raise ConnectionError("Failed to connect to S3")
        
        # 获取桶区域
        try:
            region = self.client.get_bucket_region()
            self.s3_config.region = region
        except Exception:
            # 如果获取区域失败，继续使用默认区域
            pass
    
    async def scan_objects(self, prefix: Optional[str] = None) -> AsyncIterator[S3Object]:
        """
        扫描S3对象（异步生成器）
        
        Args:
            prefix: 对象键前缀
            
        Yields:
            S3Object: 扫描到的对象
        """
        if not self.client.is_connected():
            raise RuntimeError("Client not connected. Call connect() first.")
        
        marker = self._last_key  # 从断点继续或从头开始
        prefix = prefix or self.s3_config.prefix or ''
        
        # 如果启用增量扫描，尝试从断点文件加载
        if self.scanner_config.enable_incremental and marker is None:
            loaded_key = self.checkpoint_manager.load_checkpoint()
            if loaded_key:
                print(f"Resuming from checkpoint with last_key: {loaded_key[:50]}...")
                # 使用 last_key 作为 StartAfter 分页起点
                marker = loaded_key
        
        # 如果有 marker，设置为当前分页标记
        if marker:
            self._current_marker = marker
        
        # 打印断点信息
        print(f"DEBUG: Starting scan with marker: {self._current_marker}")
        
        while not self._stopped:
            if self._paused:
                await asyncio.sleep(0.1)
                continue
            
            try:
                # 使用 marker 进行分页
                # 对于 deepinSCP，直接使用 marker 可能导致 500 错误（已知问题）
                # 这里的 list_objects 方法会自动处理 500 错误并重试
                
                # 构建分页参数
                scan_prefix = prefix
                scan_marker = self._current_marker
                scan_max_keys = self.scanner_config.max_keys_per_request
                
                if scan_marker:
                    print(f"DEBUG: Using marker for pagination: {scan_marker[:50]}...")
                
                response = self.client.list_objects(
                    prefix=scan_prefix,
                    marker=scan_marker,
                    max_keys=scan_max_keys
                )
                
                # 更新总对象数（如果需要）- list_objects 可能不返回 KeyCount，忽略此逻辑
                # if self.progress.total_objects == 0 and 'KeyCount' in response:
                #     self.progress.total_objects = response['KeyCount']
                #     print(f"DEBUG: Total objects: {self.progress.total_objects}")
                
                # 处理对象列表（支持 list_objects 和 list_objects_v2 响应格式）
                # list_objects 使用 'Contents'，list_objects_v2 使用 'Contents'
                # 某些S3兼容服务可能返回 'CommonPrefixes' 而不是 'Contents'
                contents = response.get('Contents', response.get('Contents', []))
                
                # 调试输出 - 完整响应信息
                print(f"DEBUG: list_objects_v2 response:")
                print(f"  - KeyCount: {response.get('KeyCount')}")
                print(f"  - Contents count: {len(contents)}")
                print(f"  - IsTruncated: {response.get('IsTruncated')}")
                print(f"  - ContinuationToken: {response.get('ContinuationToken')}")
                print(f"  - NextContinuationToken: {response.get('NextContinuationToken')}")
                if contents:
                    print(f"  - First object key: {contents[0].get('Key')}")
                    print(f"  - Last object key: {contents[-1].get('Key')}")
                
                for obj in contents:
                    s3_obj = S3Object(
                        key=obj.get('Key', ''),
                        bucket=self.s3_config.bucket_name,
                        path=obj.get('Key', ''),
                        last_modified=obj.get('LastModified', datetime.now()),
                        size=obj.get('Size', 0),
                        etag=obj.get('ETag', '')
                    )
                    
                    yield s3_obj
                    
                    # 更新进度
                    self.progress.scanned_objects += 1
                    self.progress.last_update = datetime.now()
                    self._last_key = s3_obj.key  # 更新最后处理的对象键
                    
                    # 如果启用增量扫描，保存断点（每次保存 last_key 作为恢复点）
                    if self.scanner_config.enable_incremental:
                        self.checkpoint_manager.save_checkpoint(self._last_key)
                        print(f"DEBUG: Saved checkpoint with key: {self._last_key[:50]}...")
                    
                    # 检查是否暂停或停止
                    if self._paused or self._stopped:
                        break
                
                # 检查是否还有更多对象
                is_truncated = response.get('IsTruncated', False)
                
                # list_objects 使用 NextMarker，list_objects_v2 使用 NextContinuationToken
                # 如果 NextMarker 不存在，使用最后一个对象的 Key
                next_marker = response.get('NextMarker')
                
                print(f"DEBUG: IsTruncated: {is_truncated}, NextMarker: {next_marker}")
                
                if is_truncated:
                    # 使用 NextMarker 或最后一个对象的 Key 作为下一页的 marker
                    if next_marker:
                        self._current_marker = next_marker
                        print(f"DEBUG: Setting marker to NextMarker: {self._current_marker[:50]}...")
                    elif contents:
                        # 使用最后一个对象的 Key 作为下一页的 StartAfter（用于 list_objects_v2）
                        self._current_marker = contents[-1].get('Key')
                        print(f"DEBUG: Using last object key as marker: {self._current_marker}")
                    else:
                        print(f"DEBUG: IsTruncated but no contents, breaking")
                        break
                else:
                    # 扫描完成
                    break
                    
            except Exception as e:
                self.progress.errors += 1
                print(f"DEBUG: Scan error - attempt {self.progress.errors}, error: {str(e)}")
                # 记录错误并重试
                if self.progress.errors <= self.scanner_config.max_retries:
                    # 重试前等待（使用指数退避）
                    wait_time = self.scanner_config.retry_delay / 1000 * (2 ** (self.progress.errors - 1))
                    print(f"DEBUG: Waiting {wait_time} seconds before retry...")
                    await asyncio.sleep(wait_time)
                    
                    # 尝试重新连接
                    print(f"DEBUG: Reconnecting to S3...")
                    try:
                        self.client.disconnect()
                        self.client.connect()
                        print(f"DEBUG: Reconnected to S3")
                    except Exception as conn_error:
                        print(f"DEBUG: Reconnection failed: {conn_error}")
                        # 连接失败也继续重试
                        continue
                    
                    # 重试时，使用相同的 marker 重新请求
                    print(f"DEBUG: Retrying with marker: {self._current_marker}")
                    continue
                else:
                    raise RuntimeError(f"Scan failed after {self.scanner_config.max_retries} retries: {str(e)}")
    
    def get_progress(self) -> ScanProgress:
        """
        获取扫描进度
        
        Returns:
            ScanProgress: 扫描进度信息
        """
        return self.progress
    
    def pause(self) -> None:
        """暂停扫描"""
        self._paused = True
    
    def resume(self) -> None:
        """恢复扫描"""
        self._paused = False
    
    def stop(self) -> None:
        """停止扫描"""
        self._stopped = True
    
    def get_last_key(self) -> Optional[str]:
        """
        获取最后扫描的对象键（用于断点续扫）
        
        Returns:
            最后一个对象的键
        """
        return self._last_key
    
    def set_last_key(self, key: str) -> None:
        """
        设置断点键（用于恢复扫描）
        
        Args:
            key: 对象键
        """
        self._last_key = key
    
    async def disconnect(self) -> None:
        """断开连接"""
        self.client.disconnect()
        self._paused = False
        self._stopped = False
    
    def clear_checkpoint(self) -> None:
        """清除断点"""
        self.checkpoint_manager.clear_checkpoint()

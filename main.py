"""主程序入口"""
import asyncio
import os
import sys
from dotenv import load_dotenv

from config.config_manager import ConfigManagerImpl
from scanner.s3_scanner import S3Credentials, S3Scanner
from scanner.s3_scanner_impl import S3ScannerImpl
from util.thread_pool import ThreadPoolImpl
from util.plugin_loader import PluginLoader, create_exporter
from model.config import SystemConfig

# 加载环境变量
load_dotenv()


async def run_scan_with_exporter(
    config: SystemConfig,
    s3_scanner: S3Scanner,
    exporter,
    thread_pool: ThreadPoolImpl
) -> None:
    """使用指定导出器运行扫描任务"""
    print(f"Starting scan with {config.exporter.type} exporter...")
    
    # 确保输出目录存在
    output_dir = config.exporter.output_dir
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")
    
    # 打开导出器
    await exporter.open()
    print(f"Exporter opened: {config.exporter.output_dir}")
    
    # 初始化扫描进度
    total_scanned = 0
    
    try:
        # 边扫描边写入，不等待批量
        async for obj in s3_scanner.scan_objects(config.s3.prefix):
            total_scanned += 1
            if total_scanned % 100 == 0:
                print(f"DEBUG: Processed {total_scanned} objects")
            
            # 立即写入每个对象
            await exporter.write([obj])
            
            # 打印进度
            progress = s3_scanner.get_progress()
            print(f"Scanned: {total_scanned} objects, Progress: {progress.scanned_objects}/{progress.total_objects}")
        
        print(f"Scan completed. Total objects scanned: {total_scanned}")
        
    except Exception as e:
        print(f"Error during scan: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # 关闭导出器
        files_saved = await exporter.close()
        if files_saved:
            print(f"Files saved: {files_saved}")


async def main():
    """主函数"""
    print("=" * 60)
    print("S3 Bucket Scanner - Main Program")
    print("=" * 60)
    
    # 初始化配置管理器
    config_manager = ConfigManagerImpl()
    
    # 使用相对于脚本位置的配置文件路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_config_path = os.path.join(script_dir, 'config', 'config.yaml')
    config_path = os.environ.get('CONFIG_PATH', default_config_path)
    try:
        config = config_manager.load_config(config_path)
        print(f"Configuration loaded from: {config_path}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    
    # 打印配置摘要
    print("\n--- Configuration Summary ---")
    print(f"Bucket: {config.s3.bucket_name}")
    print(f"Endpoint: {config.s3.endpoint}")
    print(f"Region: {config.s3.region}")
    print(f"Prefix: {config.s3.prefix or '/'}")
    print(f"Thread Pool: {config.thread_pool.core_threads} core threads, {config.thread_pool.max_threads} max threads")
    print(f"Exporter Type: {config.exporter.type}")
    print(f"Output Directory: {config.exporter.output_dir}")
    print("-" * 60)
    
    # 初始化线程池
    thread_pool = ThreadPoolImpl(config.thread_pool)
    
    # 初始化S3扫描器
    s3_scanner = S3ScannerImpl(config.s3, config.scanner)
    
    # 连接到S3桶
    try:
        await s3_scanner.connect(
            config.s3.bucket_name,
            S3Credentials(
                access_key_id=config.s3.access_key_id,
                secret_access_key=config.s3.secret_access_key,
                endpoint=config.s3.endpoint,
                region=config.s3.region,
                use_ssl=config.s3.use_ssl
            )
        )
        print("S3 connection established")
    except Exception as e:
        print(f"Failed to connect to S3: {e}")
        await thread_pool.shutdown()
        sys.exit(1)
    
    # 根据配置类型创建导出器（使用插件加载器）
    plugin_loader = PluginLoader()
    
    if config.exporter.type == 'excel':
        if config.excel is None:
            print("Error: Excel exporter selected but no excel configuration provided")
            await s3_scanner.disconnect()
            await thread_pool.shutdown()
            sys.exit(1)
        
        exporter = plugin_loader.load_exporter('excel', config)
        if exporter is None:
            print("Error: Failed to load Excel exporter")
            await s3_scanner.disconnect()
            await thread_pool.shutdown()
            sys.exit(1)
        print("Excel exporter loaded via plugin loader")
        
    elif config.exporter.type == 'csv':
        exporter = plugin_loader.load_exporter('csv', config)
        if exporter is None:
            print("Error: Failed to load CSV exporter")
            await s3_scanner.disconnect()
            await thread_pool.shutdown()
            sys.exit(1)
        print("CSV exporter loaded via plugin loader")
        
    elif config.exporter.type == 'database':
        if config.database is None:
            print("Error: Database exporter selected but no database configuration provided")
            await s3_scanner.disconnect()
            await thread_pool.shutdown()
            sys.exit(1)
        
        exporter = plugin_loader.load_exporter('database', config)
        if exporter is None:
            print("Error: Failed to load Database exporter")
            await s3_scanner.disconnect()
            await thread_pool.shutdown()
            sys.exit(1)
        print("Database exporter loaded via plugin loader")
        
    else:
        print(f"Error: Unknown exporter type: {config.exporter.type}")
        await s3_scanner.disconnect()
        await thread_pool.shutdown()
        sys.exit(1)
    
    # 运行扫描任务
    try:
        await run_scan_with_exporter(config, s3_scanner, exporter, thread_pool)
    except KeyboardInterrupt:
        print("\nScan interrupted by user")
        # 保存断点
        if config.scanner.enable_incremental:
            last_key = s3_scanner.get_last_key()
            if last_key:
                s3_scanner.checkpoint_manager.save_checkpoint(last_key)
                print(f"Checkpoint saved: {last_key}")
        await s3_scanner.disconnect()
        await thread_pool.shutdown()
        sys.exit(0)
    except Exception as e:
        print(f"Scan failed: {e}")
        await s3_scanner.disconnect()
        await thread_pool.shutdown()
        sys.exit(1)
    
    # 扫描完成，清除断点
    if config.scanner.enable_incremental:
        s3_scanner.clear_checkpoint()
        print("Checkpoint cleared")
    
    # 关闭资源
    await s3_scanner.disconnect()
    await thread_pool.shutdown()
    
    print("=" * 60)
    print("Scan completed successfully!")
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())

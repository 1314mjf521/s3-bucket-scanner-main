import sys
import subprocess

def ensure_dependency_installed(module_name, install_name=None):
    """
    确保指定的模块已安装，如果未安装则自动安装。
    :param module_name: 模块名称（用于导入）
    :param install_name: pip 安装名称（如果与模块名称不同）
    """
    try:
        __import__(module_name)
    except ImportError:
        print(f"Module '{module_name}' is not installed. Attempting to install...")
        install_name = install_name or module_name
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", install_name])
            print(f"Module '{module_name}' installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install module '{module_name}'. Error: {e}")
            sys.exit(1)

# 确保所需依赖已安装
def ensure_dependencies():
    """
    确保所有必要的依赖已安装。
    """
    dependencies = {
        "boto3": "boto3",
        "yaml": "pyyaml",
    }
    for module, install_name in dependencies.items():
        ensure_dependency_installed(module, install_name)

# 在程序开始时确保依赖已安装
ensure_dependencies()

# 在确保依赖安装后再导入模块
import boto3
import yaml
import os
import logging
import datetime
import traceback
import platform
import migration_core

def get_absolute_path(relative_path):
    """
    获取相对于脚本所在目录的绝对路径。
    :param relative_path: 相对路径
    :return: 绝对路径
    """
    try:
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))  # 修改为 sys.argv[0]，确保在可执行文件中正确解析路径
        return os.path.join(base_dir, relative_path)
    except Exception as e:
        print(f"Failed to resolve absolute path for {relative_path}: {e}")
        sys.exit(1)

def load_settings(file_path):
    """
    加载配置文件。
    :param file_path: 配置文件路径
    """
    absolute_path = get_absolute_path(file_path)
    if not os.path.exists(absolute_path):
        print(f"Settings file not found at {absolute_path}. Please ensure the file exists.")
        sys.exit(1)
    try:
        with open(absolute_path, 'r', encoding='utf-8') as file:
            settings = yaml.safe_load(file)
            return settings
    except Exception as e:
        print(f"Failed to load settings from {absolute_path}: {e}")
        sys.exit(1)

def connect_to_s3(settings, bucket_type):
    try:
        bucket_settings = settings[bucket_type]
        if (bucket_settings.get('use_aws', False)):
            s3 = boto3.client(
                's3',
                aws_access_key_id=bucket_settings['aws_access_key_id'],
                aws_secret_access_key=bucket_settings['aws_secret_access_key'],
                region_name=bucket_settings.get('region', 'us-east-1'),
                endpoint_url=bucket_settings.get('endpoint_url')
            )
            print(f"Connected to AWS S3 ({bucket_type}) with region: {bucket_settings.get('region', 'us-east-1')}")
        else:
            s3 = boto3.client(
                's3',
                aws_access_key_id=bucket_settings['custom_access_key_id'],
                aws_secret_access_key=bucket_settings['custom_secret_access_key'],
                endpoint_url=bucket_settings['custom_endpoint_url']
            )
            print(f"Connected to custom S3 storage ({bucket_type}) with endpoint: {bucket_settings['custom_endpoint_url']}")
        return s3
    except KeyError as e:
        print(f"Missing configuration key for {bucket_type}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred while connecting to {bucket_type} S3: {e}")
        sys.exit(1)

def connect_to_s3_with_validation(settings, bucket_type):
    """
    尝试连接到 S3 存储桶，并验证连接是否成功。
    :param settings: 配置字典
    :param bucket_type: 'source' 或 'destination'
    :return: S3 客户端对象
    """
    try:
        s3_client = connect_to_s3(settings, bucket_type)
        bucket_name = settings[bucket_type]['custom_region_name']
        response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
        print(f"Successfully connected to {bucket_type} bucket: {bucket_name}")
        return s3_client
    except KeyError as e:
        error_message = f"Configuration key missing for {bucket_type}: {e}"
        print(error_message)
        logging.error(error_message)
        sys.exit(1)
    except boto3.exceptions.Boto3Error as e:
        error_message = f"Boto3 error while connecting to {bucket_type} bucket: {e}"
        print(error_message)
        logging.error(error_message)
        sys.exit(1)
    except Exception as e:
        error_message = f"Unexpected error while connecting to {bucket_type} bucket: {e}"
        print(error_message)
        logging.error(error_message)
        logging.error(traceback.format_exc())
        sys.exit(1)

def check_environment():
    """
    检查程序运行所需的环境是否满足。
    """
    try:
        # 检查是否有写入权限
        test_path = os.path.abspath('./test_permission')
        with open(test_path, 'w', encoding='utf-8') as test_file:
            test_file.write("test")
        os.remove(test_path)
        print("Environment check passed: Write permissions are available.")
    except PermissionError as e:
        print(f"Environment check failed: No write permissions. Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Environment check failed: {e}")
        sys.exit(1)

def prepare_log_path(settings, base_path):
    """
    确保日志路径适配当前操作系统，并创建必要的目录和文件。
    :param settings: 配置字典
    :param base_path: 基准路径，用于生成日志文件路径
    """
    try:
        # 将日志路径解析为基于 base_path 的绝对路径
        log_location = os.path.join(base_path, 'migration.log')
        log_dir = os.path.dirname(log_location)

        # 确保日志目录存在
        if not os.path.exists(log_dir):
            print(f"Creating log directory: {log_dir}")
            os.makedirs(log_dir, exist_ok=True)

        # 确保日志文件存在
        if not os.path.exists(log_location):
            print(f"Creating log file: {log_location}")
            with open(log_location, 'w', encoding='utf-8') as log_file:
                log_file.write("")  # 创建空日志文件

        settings['logging_config']['log_location'] = log_location
        print(f"Log path prepared: {log_location}")
    except PermissionError as e:
        print(f"Permission error while preparing log path: {e}")
        raise RuntimeError(f"Failed to prepare log path due to permission error: {e}")
    except Exception as e:
        print(f"Failed to prepare log path: {e}")
        raise RuntimeError(f"Failed to prepare log path: {e}")

def init_logger(settings):
    """
    初始化日志记录器，确保日志文件路径正确并支持写入。
    """
    try:
        log_location = settings['logging_config']['log_location']
        logging.basicConfig(
            filename=log_location,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        logging.info("Logger initialized successfully.")
        print(f"Logger initialized. Logs will be written to: {log_location}")
    except PermissionError as e:
        print(f"Permission error while initializing logger: {e}")
        raise RuntimeError(f"Failed to initialize logger due to permission error: {e}")
    except Exception as e:
        print(f"Failed to initialize logger: {e}")
        raise RuntimeError(f"Failed to initialize logger: {e}")

SETTINGS = None

def main():
    try:
        global SETTINGS

        # 检查环境
        check_environment()

        try:
            settings_file = 'setting.yml'  # 使用相对路径
            SETTINGS = load_settings(settings_file)
        except Exception as e:
            print(f"Failed to load settings: {e}")
            sys.exit(1)

        try:
            base_path = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), 'path'))  # 修改为 sys.argv[0]
            if not os.path.exists(base_path):
                print(f"Creating base directory: {base_path}")
                os.makedirs(base_path)

            SETTINGS['data_migration_config']['file_list_path'] = os.path.join(base_path, 'file_list.txt')
            SETTINGS['logging_config']['success_record']['file_path'] = os.path.join(base_path, 'Successful_record.txt')
            SETTINGS['logging_config']['error_record']['file_path'] = os.path.join(base_path, 'error_record.txt')

            # 准备日志路径并初始化日志记录器
            prepare_log_path(SETTINGS, base_path)
            init_logger(SETTINGS)
        except RuntimeError as e:
            print(f"Critical error during log initialization: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Failed to prepare paths or initialize logger: {e}")
            sys.exit(1)

        try:
            file_list_path = SETTINGS['data_migration_config']['file_list_path']
            record_file = SETTINGS['logging_config']['success_record']['file_path']
            if not file_list_path or not record_file:
                raise ValueError("Missing required paths in the configuration.")
        except Exception as e:
            print(f"Configuration validation error: {e}")
            logging.error(f"Configuration validation error: {e}")
            sys.exit(1)

        try:
            thread_count = SETTINGS.get('data_migration_config', {}).get('thread_count', 1)
            use_multithreading = thread_count > 1

            max_pages_per_iteration = thread_count
            SETTINGS['data_migration_config']['max_pages_per_iteration'] = max_pages_per_iteration

            if use_multithreading:
                print(f"[{datetime.datetime.now()}] Using {thread_count} threads for data migration.")
            else:
                print(f"[{datetime.datetime.now()}] Using single-threaded mode for data migration.")
        except Exception as e:
            print(f"Error while configuring threading: {e}")
            logging.error(f"Error while configuring threading: {e}")
            sys.exit(1)

        try:
            source_s3_client = connect_to_s3_with_validation(SETTINGS, 'source')
            destination_s3_client = connect_to_s3_with_validation(SETTINGS, 'destination')
        except Exception as e:
            print(f"Error during S3 connection validation: {e}")
            logging.error(f"Error during S3 connection validation: {e}")
            sys.exit(1)

        try:
            migration_core.start_migration(
                source_s3_client,
                destination_s3_client,
                SETTINGS,
                use_multithreading,
                thread_count
            )
        except Exception as e:
            logging.error(f"[{datetime.datetime.now()}] An error occurred during migration: {e}")
            print(f"[{datetime.datetime.now()}] An error occurred during migration: {e}")
            logging.error(traceback.format_exc())
            sys.exit(1)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        traceback.print_exc()  # 打印详细的堆栈信息
        input("Press Enter to exit...")  # 防止闪退，等待用户按下回车键

if __name__ == "__main__":
    main()

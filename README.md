# S3 Bucket Scanner

高性能S3桶扫描工具，支持多线程并行处理和配置驱动架构。

## 功能特性

- 扫描S3桶中所有对象的元数据
- 支持Excel和数据库两种导出方式
- 多线程并行处理
- 配置驱动架构
- 断点续扫支持
- 十亿级文件规模处理能力
- **S3协议兼容**：完全兼容所有S3协议平台（MinIO、阿里云OSS、腾讯云COS等）

## 项目结构

```
s3-bucket-scanner-main/
├── config/           # 配置管理模块
│   ├── __init__.py
│   └── config_manager.py
├── scanner/          # S3扫描模块
│   ├── __init__.py
│   └── s3_scanner.py
├── exporter/         # 数据导出模块
│   ├── __init__.py
│   └── exporter.py
├── model/            # 数据模型
│   ├── __init__.py
│   ├── config.py
│   └── s3_object.py
├── util/             # 工具类
│   ├── __init__.py
│   └── thread_pool.py
├── main.py           # 主程序入口
├── config/           # 配置文件目录
│   └── config.yaml
└── requirements.txt
```

## 快速开始

1. 安装依赖
```bash
pip install -r requirements.txt
```

2. 配置S3连接信息
编辑 `config/config.yaml` 文件，设置S3连接参数

3. 运行程序
```bash
python main.py
```

## 配置说明

配置文件使用YAML格式，主要配置项：

- `scanner`: 扫描器配置
- `exporter`: 导出器配置
- `threadPool`: 线程池配置
- `s3`: S3连接配置（兼容所有S3协议平台，如MinIO、阿里云OSS、腾讯云COS等）
- `excel`: Excel导出配置
- `database`: 数据库导出配置

### S3 兼容性说明

本工具完全兼容所有S3协议平台，包括但不限于：

- **Amazon S3**：默认配置，直接使用
- **MinIO**：设置 `endpoint` 为 MinIO 服务地址
- **阿里云 OSS**：设置 `endpoint` 为 OSS endpoint
- **腾讯云 COS**：设置 `endpoint` 为 COS endpoint
- **华为云 OBS**：设置 `endpoint` 为 OBS endpoint
- **本地私有云 S3**：设置 `endpoint` 为本地 S3 服务地址

### 不同 S3 平台配置示例

#### Amazon S3（默认）
```yaml
s3:
  endpoint: https://s3.amazonaws.com
  region: us-east-1
  accessKeyId: YOUR_ACCESS_KEY
  secretAccessKey: YOUR_SECRET_KEY
  bucketName: my-bucket
```

#### MinIO
```yaml
s3:
  endpoint: http://localhost:9000
  region: us-east-1
  accessKeyId: minioadmin
  secretAccessKey: minioadmin
  bucketName: my-bucket
  useSSL: false
```

#### 阿里云 OSS
```yaml
s3:
  endpoint: https://oss-cn-hangzhou.aliyuncs.com
  region: cn-hangzhou
  accessKeyId: YOUR_ACCESS_KEY
  secretAccessKey: YOUR_SECRET_KEY
  bucketName: my-bucket
```

#### 腾讯云 COS
```yaml
s3:
  endpoint: https://cos.ap-shanghai.myqcloud.com
  region: ap-shanghai
  accessKeyId: YOUR_ACCESS_KEY
  secretAccessKey: YOUR_SECRET_KEY
  bucketName: my-bucket
```

#### 深信服（无需 region）
```yaml
s3:
  endpoint: https://s3.example.com
  accessKeyId: YOUR_ACCESS_KEY
  secretAccessKey: YOUR_SECRET_KEY
  bucketName: my-bucket
```

## 开发

```bash
# 运行程序
python main.py

# 运行测试
pytest
```

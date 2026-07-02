# S3 Bucket Scanner 使用手册

## 目录

- [项目介绍](#项目介绍)
- [安装指南](#安装指南)
- [配置说明](#配置说明)
- [快速开始](#快速开始)
- [高级用法](#高级用法)
- [常见问题](#常见问题)

---

## 项目介绍

S3 Bucket Scanner 是一个高性能的 S3 桶扫描工具，专为大规模对象扫描设计。它支持：

- **多线程并行处理**：利用线程池加速扫描和导出
- **配置驱动架构**：通过 YAML 配置文件灵活控制扫描行为
- **断点续扫**：支持中断后恢复扫描进度
- **双导出模式**：支持导出到 Excel 或数据库
- **大文件支持**：Excel 导出支持自动分 sheet 和分文件
- **增量扫描**：支持基于前缀的增量扫描
- **S3协议兼容**：完全兼容所有S3协议平台（MinIO、阿里云OSS、腾讯云COS等）

### 典型应用场景

- S3 桶资产盘点
- 对象存储迁移前的元数据采集
- 大规模数据目录生成
- 数据合规性检查
- 跨区域桶同步验证

---

## 安装指南

### 系统要求

- Python 3.8 或更高版本
- pip 包管理器
- S3 访问凭证（Access Key ID 和 Secret Access Key）或使用公共桶

### 安装步骤

1. **克隆或下载项目**

```bash
cd s3-bucket-scanner-main
```

2. **创建虚拟环境（推荐）**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **验证安装**

```bash
python -c "import boto3; import yaml; import openpyxl; print('All dependencies installed successfully')"
```

---

## 配置说明

### 配置文件位置

配置文件位于 `config/config.yaml`，支持以下配置项：

### 完整配置示例

```yaml
scanner:
  maxKeysPerRequest: 1000          # 每次请求最大键数（1-1000）
  maxRetries: 3                    # 最大重试次数
  retryDelay: 1000                 # 重试延迟（毫秒）
  enableIncremental: false         # 是否启用增量扫描

exporter:
  type: excel                      # 导出类型：excel 或 database
  outputDir: ./output              # 输出目录

threadPool:
  coreThreads: 4                   # 核心线程数
  maxThreads: 10                   # 最大线程数
  queueSize: 1000                  # 队列大小
  keepAliveTime: 60                # 线程存活时间（秒）

s3:
  endpoint: https://s3.amazonaws.com  # S3端点URL（兼容所有S3协议平台）
  region: us-east-1                   # 区域（可选，某些S3平台如深信服不需要，可留空）
  accessKeyId: ${AWS_ACCESS_KEY_ID}   # 访问密钥ID（支持环境变量，公共桶可留空）
  secretAccessKey: ${AWS_SECRET_ACCESS_KEY}  # 密钥（支持环境变量，公共桶可留空）
  bucketName: my-bucket               # 桶名称
  prefix: /                           # 扫描前缀（用于过滤特定目录）
  useSSL: true                        # 是否使用SSL加密连接

excel:
  fileName: s3_objects               # Excel文件名
  maxRowsPerSheet: 1000000           # 每张表最大行数
  splitFile: true                    # 是否分文件

database:
  type: mysql                        # 数据库类型：mysql 或 postgresql
  host: localhost                    # 数据库主机
  port: 3306                         # 数据库端口
  database: s3_scanner               # 数据库名称
  username: root                     # 用户名
  password: password                 # 密码
  tableName: s3_objects              # 表名
  batchSize: 1000                    # 批量写入大小
```

### 配置项详细说明

#### Scanner 配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| maxKeysPerRequest | int | 1000 | 每次 S3 API 请求返回的最大对象数（范围 1-1000） |
| maxRetries | int | 3 | 扫描失败时的最大重试次数 |
| retryDelay | int | 1000 | 重试延迟（毫秒） |
| enableIncremental | bool | false | 是否启用增量扫描模式 |

#### Exporter 配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| type | string | excel | 导出类型，可选值：`excel` 或 `database` |
| outputDir | string | ./output | 输出目录路径 |

#### ThreadPool 配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| coreThreads | int | 4 | 线程池核心线程数 |
| maxThreads | int | 10 | 线程池最大线程数 |
| queueSize | int | 1000 | 任务队列大小 |
| keepAliveTime | int | 60 | 空闲线程存活时间（秒） |

#### S3 配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| endpoint | string | https://s3.amazonaws.com | S3 服务端点 URL（兼容所有S3协议平台） |
| region | string | - | 区域（可选，某些S3平台如深信服不需要） |
| accessKeyId | string | - | 访问密钥 ID（支持环境变量，公共桶可留空） |
| secretAccessKey | string | - | 密钥（支持环境变量，公共桶可留空） |
| bucketName | string | - | 要扫描的桶名称 |
| prefix | string | / | 对象键前缀（用于过滤） |
| useSSL | bool | true | 是否使用 SSL 加密连接 |

### S3 兼容性说明

本工具完全兼容所有 S3 协议平台，包括但不限于：

- **Amazon S3**：默认配置，直接使用
- **MinIO**：设置 `endpoint` 为 MinIO 服务地址
- **阿里云 OSS**：设置 `endpoint` 为 OSS endpoint
- **腾讯云 COS**：设置 `endpoint` 为 COS endpoint
- **华为云 OBS**：设置 `endpoint` 为 OBS endpoint
- **本地私有云 S3**：设置 `endpoint` 为本地 S3 服务地址

#### 不同 S3 平台配置示例

**Amazon S3（默认）**
```yaml
s3:
  endpoint: https://s3.amazonaws.com
  region: us-east-1
  accessKeyId: YOUR_ACCESS_KEY
  secretAccessKey: YOUR_SECRET_KEY
  bucketName: my-bucket
```

**MinIO**
```yaml
s3:
  endpoint: http://localhost:9000
  region: us-east-1
  accessKeyId: minioadmin
  secretAccessKey: minioadmin
  bucketName: my-bucket
  useSSL: false
```

**阿里云 OSS**
```yaml
s3:
  endpoint: https://oss-cn-hangzhou.aliyuncs.com
  region: cn-hangzhou
  accessKeyId: YOUR_ACCESS_KEY
  secretAccessKey: YOUR_SECRET_KEY
  bucketName: my-bucket
```

**腾讯云 COS**
```yaml
s3:
  endpoint: https://cos.ap-shanghai.myqcloud.com
  region: ap-shanghai
  accessKeyId: YOUR_ACCESS_KEY
  secretAccessKey: YOUR_SECRET_KEY
  bucketName: my-bucket
```

**深信服（无需 region）**
```yaml
s3:
  endpoint: https://s3.example.com
  accessKeyId: YOUR_ACCESS_KEY
  secretAccessKey: YOUR_SECRET_KEY
  bucketName: my-bucket
```

#### Excel 配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| fileName | string | s3_objects | Excel 文件名（不包含扩展名） |
| maxRowsPerSheet | int | 1000000 | 每个工作表的最大行数 |
| splitFile | bool | true | 超出行数时是否创建新文件 |

#### Database 配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| type | string | mysql | 数据库类型，可选值：`mysql` 或 `postgresql` |
| host | string | localhost | 数据库主机地址 |
| port | int | 3306 | 数据库端口 |
| database | string | - | 数据库名称 |
| username | string | - | 数据库用户名 |
| password | string | - | 数据库密码 |
| tableName | string | - | 存储扫描结果的表名 |
| batchSize | int | 1000 | 批量写入的记录数 |

### 环境变量支持

配置文件支持使用环境变量，格式为 `${VARIABLE_NAME}`：

```yaml
s3:
  accessKeyId: ${AWS_ACCESS_KEY_ID}
  secretAccessKey: ${AWS_SECRET_ACCESS_KEY}
```

在运行前设置环境变量：

```bash
# Windows
set AWS_ACCESS_KEY_ID=your_access_key
set AWS_SECRET_ACCESS_KEY=your_secret_key

# Linux/Mac
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
```

或者创建 `.env` 文件：

```bash
# .env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

---

## 快速开始

### 第一次使用

1. **配置 S3 连接信息**

编辑 `config/config.yaml` 文件，设置以下必填项：

```yaml
s3:
  endpoint: https://s3.amazonaws.com  # S3端点URL（兼容所有S3协议平台）
  region: us-east-1                   # 区域（可选，某些S3平台如深信服不需要）
  accessKeyId: YOUR_ACCESS_KEY_ID     # 访问密钥ID
  secretAccessKey: YOUR_SECRET_ACCESS_KEY  # 密钥
  bucketName: YOUR_BUCKET_NAME        # 桶名称
```

**不同 S3 平台配置示例：**

**MinIO**
```yaml
s3:
  endpoint: http://localhost:9000
  region: us-east-1
  accessKeyId: minioadmin
  secretAccessKey: minioadmin
  bucketName: my-bucket
  useSSL: false
```

**阿里云 OSS**
```yaml
s3:
  endpoint: https://oss-cn-hangzhou.aliyuncs.com
  region: cn-hangzhou
  accessKeyId: YOUR_ACCESS_KEY
  secretAccessKey: YOUR_SECRET_KEY
  bucketName: my-bucket
```

**深信服（无需 region）**
```yaml
s3:
  endpoint: https://s3.example.com
  accessKeyId: YOUR_ACCESS_KEY
  secretAccessKey: YOUR_SECRET_KEY
  bucketName: my-bucket
```

2. **运行扫描**

```bash
python main.py
```

3. **查看结果**

- Excel 导出：`output/s3_objects.xlsx`
- 数据库导出：检查配置的数据库表

### 扫描特定前缀

如果只想扫描特定目录下的对象，修改配置：

```yaml
s3:
  prefix: /folder/subfolder/  # 只扫描此前缀下的对象
```

### 使用数据库导出

修改配置文件：

```yaml
exporter:
  type: database
  outputDir: ./output

database:
  type: mysql
  host: localhost
  port: 3306
  database: s3_scanner
  username: root
  password: your_password
  tableName: s3_objects
  batchSize: 1000
```

运行程序，数据将自动写入数据库。

---

## 高级用法

### 断点续扫

当扫描大量对象时，可能会因为网络问题或程序中断而中断。启用断点续扫功能：

```yaml
scanner:
  enableIncremental: true
```

程序会自动记录最后扫描的对象键，下次运行时从断点继续。

### 批量扫描多个桶

创建多个配置文件，分别指定不同的桶：

```bash
# config/bucket1.yaml
s3:
  bucketName: bucket1

# config/bucket2.yaml
s3:
  bucketName: bucket2
```

运行时指定配置文件：

```bash
CONFIG_PATH=config/bucket1.yaml python main.py
CONFIG_PATH=config/bucket2.yaml python main.py
```

### 自定义输出目录

```yaml
exporter:
  outputDir: ./custom_output
```

### 调整线程池大小

根据系统资源和网络带宽调整线程池：

```yaml
threadPool:
  coreThreads: 8    # 增加核心线程数
  maxThreads: 20    # 增加最大线程数
```

### 大文件处理优化

当扫描结果超过 Excel 单表限制时：

```yaml
excel:
  maxRowsPerSheet: 1000000  # 每个 sheet 100 万行
  splitFile: true           # 自动分文件
```

程序会自动创建 `s3_objects.xlsx`、`s3_objects_2.xlsx` 等文件。

### 增量扫描

只扫描新增或修改的对象：

```yaml
scanner:
  enableIncremental: true
```

首次运行会扫描所有对象，记录最后的键。后续运行时，只扫描该键之后的对象。

---

## 常见问题

### 1. 连接 S3 失败

**问题**：`Failed to connect to S3`

**可能原因**：
- AWS 凭证错误
- 网络连接问题
- S3 端点或区域配置错误

**解决方案**：
```bash
# 检查凭证
echo %AWS_ACCESS_KEY_ID%
echo %AWS_SECRET_ACCESS_KEY%

# 验证网络连接
ping s3.amazonaws.com
```

### 1.1 连接 MinIO 或其他 S3 兼容服务失败

**问题**：`Failed to connect to S3`

**可能原因**：
- 端点 URL 配置错误
- 凭证错误
- 网络连接问题
- SSL 证书问题（自签名证书）

**解决方案**：
```bash
# 检查端点是否可访问
curl http://localhost:9000

# 对于 MinIO，确保 useSSL 为 false
s3:
  endpoint: http://localhost:9000
  useSSL: false
```

### 2. 权限不足

**问题**：`Access Denied` 或 `403 Forbidden`

**解决方案**：
确保 AWS 用户具有以下权限：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetObject"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket",
        "arn:aws:s3:::your-bucket/*"
      ]
    }
  ]
}
```

### 3. Excel 文件过大

**问题**：单个 Excel 文件超过 1000 万行

**解决方案**：
- 启用分文件：`splitFile: true`
- 调整每表行数：`maxRowsPerSheet: 1000000`

### 4. 扫描速度慢

**优化建议**：
1. 增加线程数
2. 减小 `maxKeysPerRequest`（网络慢时）
3. 使用就近的 S3 区域

### 5. 数据库连接失败

**问题**：`Failed to connect to MySQL`

**解决方案**：
- 检查数据库服务是否运行
- 验证用户名密码
- 确认网络连通性

```yaml
database:
  host: 127.0.0.1  # 使用 IP 而非 localhost
  port: 3306
```

### 6. S3 兼容服务连接问题

**问题**：连接 MinIO、阿里云 OSS 等 S3 兼容服务失败

**解决方案**：
- 确保 `endpoint` 正确配置
- 对于 MinIO，设置 `useSSL: false`
- 对于阿里云 OSS，设置正确的 region
- 对于腾讯云 COS，设置正确的 endpoint

### 7. 配置文件格式错误

**问题**：`Configuration error: ...`

**解决方案**：
使用 YAML 格式验证工具检查配置文件：

```bash
# 安装 yaml-lint
npm install -g yaml-lint

# 验证配置
yaml-lint config/config.yaml
```

### 8. 环境变量未生效

**问题**：配置文件中的 `${VARIABLE}` 未被替换

**解决方案**：
确保在运行前设置环境变量：

```bash
# Windows
set AWS_ACCESS_KEY_ID=your_key
set AWS_SECRET_ACCESS_KEY=your_secret
python main.py

# Linux/Mac
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
python main.py
```

### 9. 扫描进度查看

程序运行时会实时打印进度：

```
Scanned: 1000 objects, Progress: 1000/50000
Scanned: 2000 objects, Progress: 2000/50000
...
```

### 10. 日志输出

程序会将错误信息输出到控制台。如需保存日志：

```bash
python main.py > scan.log 2>&1
```

### 11. 性能调优

**小规模扫描（< 10000 对象）**：
```yaml
threadPool:
  coreThreads: 2
  maxThreads: 4
```

**大规模扫描（> 1000000 对象）**：
```yaml
threadPool:
  coreThreads: 16
  maxThreads: 32
  queueSize: 5000
```

### 12. S3 兼容服务性能调优

**MinIO 性能调优**：
```yaml
threadPool:
  coreThreads: 8
  maxThreads: 16
  queueSize: 2000

scanner:
  maxKeysPerRequest: 500  # 减小每次请求的键数，提高并发性
```

**阿里云 OSS 性能调优**：
```yaml
threadPool:
  coreThreads: 4
  maxThreads: 8
  queueSize: 1000

scanner:
  maxRetries: 5  # 增加重试次数
  retryDelay: 2000  # 增加重试延迟
```

---

## 技术支持

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送邮件
- 查看项目文档

---

## 许可证

本项目采用 MIT 许可证。
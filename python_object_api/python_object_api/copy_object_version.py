import boto3
import botocore


def copy_object(src_bucket_name, src_object_name, src_object_version, dest_bucket_name, dest_object_name):
    access_key = "L8O3KRQZTXGVDIBQ0WON"  # 使用EDS web界面创建的对象存储用户，此处填用户的access key
    secret_key = "Bm0kLoFdLu70RKTOtjdP5Q9oOVDgEXHOmbrelxeb"  # 使用EDS web界面创建的对象存储用户，此处填用户的secret key
    end_point = "http://10.212.27.56:12001"  # EDS对象存储的地址:对象存储服务的端口号
    config = botocore.config.Config(
      connect_timeout=1200,  # 建立连接的超时时间（单位：秒）
      max_pool_connections=20,  # 允许打开的最大HTTP连接数
      retries={"max_attempts": 4},  # 请求失败后最大的重试次数
      s3={'addressing_style': 'path'}  # EDS公有云只支持子域名的方式
    )

    s3client = boto3.client(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        endpoint_url=end_point,
        config=config
    )
    try:
        copy_source = "/{0}/{1}?versionId={2}".format(src_bucket_name, src_object_name, src_object_version)  # 格式按照这个来，否者EDS不接受该请求
        response = s3client.copy_object(CopySource=copy_source, Bucket=dest_bucket_name, Key=dest_object_name)
    except botocore.exceptions.ClientError as e:
        print(
            "ServiceError: %s\n"
            "status_code: %s\n"
            "error_code: %s\n" % (
                e,
                e.response['ResponseMetadata']['HTTPStatusCode'],  # 错误http状态码
                e.response["Error"]['Code'],  # EDS服务器定义错误类型
            ))
    except botocore.exceptions.ParamValidationError as e:
        print(
            "ClientError: %s\n"
            "message: %s\n"
            % (
                e,
                e.fmt
           ))


if __name__ == "__main__":
    src_bucket_name = "aaa"
    src_object_name = "Python-3.6.15.tgz"
    src_object_version = "1e8bc235fd432d5d540400000001C1387"
    dest_bucket_name = "new-bucket-7ac4f020"
    dest_obejct_name = "copy_" + src_object_name
    copy_object(src_bucket_name, src_object_name, src_object_version, dest_bucket_name, dest_obejct_name)

# -*- coding: UTF-8 -*-
import boto3
import botocore


def get_object(bucket_name, object_name, version_id):
    access_key = "L8O3KRQZTXGVDIBQ0WON"  # 使用EDS web界面创建的对象存储用户，此处填用户的access key
    secret_key = "Bm0kLoFdLu70RKTOtjdP5Q9oOVDgEXHOmbrelxeb"  # 使用EDS web界面创建的对象存储用户，此处填用户的secret key
    end_point = "http://10.212.27.56:12001"  # EDS对象存储的地址:对象存储服务的端口号
    config = botocore.config.Config(
      connect_timeout=1200,  # 建立连接的超时时间（单位：秒）
      max_pool_connections=20,  # 允许打开的最大HTTP连接数
      retries={"max_attempts": 4},  # 请求失败后最大的重试次数
      s3={'addressing_style': 'path'}  # EDS公有云只支持子域名的方式
    )

    try:
        s3client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=end_point,
            config=config
        )

        response = s3client.get_object(Bucket=bucket_name, Key=object_name, VersionId=version_id)
        print(response)
    except Exception as e:
        raise e


if __name__ == "__main__":
    bucket_name = "aaa"
    object_name = "Python-3.6.15.tgz"
    version_id = "1e8bc235fd432d5d540400000001C1387"
    get_object(bucket_name, object_name, version_id)

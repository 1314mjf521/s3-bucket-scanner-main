# -*- coding: UTF-8 -*-
import boto3
import botocore


def list_object_versions(bucket_name, object_name):
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
        response = s3client.list_object_versions(
            Bucket=bucket_name,
            Prefix=object_name,
        )

        print(response["Versions"])
    except Exception as e:
        raise e


if __name__ == "__main__":
    bucket_name = "aaa"
    object_name = "Python-3.6.15.tgz"
    list_object_versions(bucket_name, object_name)

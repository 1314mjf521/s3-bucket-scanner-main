# -*- coding: UTF-8 -*-
import boto3
import botocore


def multipart_upload(local_object_path, bucket_name, object_name):
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
    init_upload = s3client.create_multipart_upload(Bucket=bucket_name, Key=object_name)
    upload_id = init_upload["UploadId"]

    index = 0
    slice_size = 10 * 1024 * 1024
    with open(local_object_path, "rb") as fp:
        while True:
            index += 1
            part = fp.read(slice_size)
            if not part:
                break
            upload_part = s3client.upload_part(Bucket=bucket_name, Key=object_name,
                                               PartNumber=index, UploadId=upload_id, Body=part)
            print(upload_part)

    r_parts = s3client.list_parts(Bucket=bucket_name, Key=object_name, UploadId=upload_id)
    part_etags = []
    for part in r_parts["Parts"]:
        part_etags.append({"PartNumber": part["PartNumber"], "ETag": part["ETag"]})

    s3client.complete_multipart_upload(Bucket=bucket_name, Key=object_name, UploadId=upload_id, MultipartUpload={
        'Parts': part_etags
    })


if __name__ == "__main__":
    local_object_path = "/home/workspace/obj_python/Python-3.6.15.tgz"
    bucket_name = "new_bucket"
    object_name = "Python-3.6.15.tgz"
    multipart_upload(local_object_path, bucket_name, object_name)

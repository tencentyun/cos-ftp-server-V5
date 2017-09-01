# -*- coding:utf-8 -*-

import os
import sys
import glob
import multiprocessing
import logging
import qcloud_cos.cos_client

logger = logging.getLogger(__name__)


class MultipartUpload(object):

    MaxiumPartNum = 10000

    ResponseDataParser = (
        ('Bucket', '_bucket_name', None),
        ('Key', '_key_name', None),
        ('UploadId','_upload_id',None)
    )

    def __init__(self, cos_client, dict_response):
        self._cos_client = cos_client

        for response_name, attr_name, default_value in MultipartUpload.ResponseDataParser:
            if response_name == "Bucket":
                dict_response[response_name] = dict_response[response_name].split("-")[0]       # V5 返回回来的是bucket-appid这种格式
            setattr(self, attr_name, dict_response[response_name] or default_value)
            # TODO 要不要持有文件路径

    def upload_part(self, content, part_num):
        dict_response = self._cos_client.upload_part(
            Bucket=self._bucket_name, Key=self._key_name,
            UploadId=self._upload_id, PartNumber=part_num,
            Body=content
        )

        return dict_response           # xxx

    def complete_upload(self):
        dict_response = self._cos_client.list_parts(Bucket=self._bucket_name,
                                                    Key = self._key_name,
                                                    UploadId=self._upload_id)
        part_list = dict_response["Part"]

        dict_response = self._cos_client.complete_multipart_upload(Bucket=self._bucket_name,
                                                                   Key=self._key_name,
                                                                   UploadId=self._upload_id,
                                                                   MultipartUpload={"Part":part_list})
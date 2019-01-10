# -*- coding:utf-8 -*-

import logging
import threading

from qcloud_cos.cos_exception import CosException

logger = logging.getLogger(__name__)


class MultipartUpload(object):
    MaxiumPartNum = 10000

    ResponseDataParser = (
        ('Bucket', '_bucket_name', None),
        ('Key', '_key_name', None),
        ('UploadId', '_upload_id', None)
    )

    def __init__(self, cos_client, dict_response):
        self._cos_client = cos_client
        for response_name, attr_name, default_value in MultipartUpload.ResponseDataParser:
            setattr(self, attr_name, dict_response[response_name] or default_value)

        self._multipart_upload = dict()
        self._multipart_upload['Part'] = list()

    def upload_part(self, content, part_num, callback=None):
        dict_response = None
        try:
            dict_response = self._cos_client.upload_part(
                Bucket=self._bucket_name, Key=self._key_name,
                UploadId=self._upload_id, PartNumber=part_num,
                Body=content
            )
        except Exception as e:
            if callback is not None:
                callback(part_num, False)  # 如果上传成功，需要回调通知
                raise e

        dict_etag = dict()
        dict_etag['ETag'] = dict_response['ETag'].strip('"')
        dict_etag['PartNumber'] = part_num
        self._multipart_upload['Part'].append(dict_etag)

        if callback is not None:
            callback(part_num, True)

        return dict_response  # xxx

    def complete_upload(self):
        # 首先，对multipart进行排序
        self._multipart_upload['Part'] = sorted(self._multipart_upload['Part'], key=lambda part: part["PartNumber"])

        try:
            dict_response = self._cos_client.complete_multipart_upload(Bucket=self._bucket_name,
                                                                       Key=self._key_name,
                                                                       UploadId=self._upload_id,
                                                                       MultipartUpload=self._multipart_upload)
        except CosException as e:
            logger.error("Complete upload failed. File:{0} Thread:{1}".format(self._key_name,
                                                                              threading.currentThread().getName()))
            raise e
        except Exception as e:
            logger.error("Complete upload failed. File:{0} Thread:{1}".format(self._key_name,
                                                                              threading.currentThread().getName()))

# -*- coding:utf-8 -*-

import threading
import logging
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
            if response_name == "Bucket":
                bucket_appid = dict_response[response_name].split("-")
                del bucket_appid[-1]
                bucket = "-".join(bucket_appid)
                dict_response[response_name] = bucket       # V5 返回回来的是bucket-appid这种格式
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
            logger.exception("upload part_num:{0} occurs an exception.".format(str(part_num).encode("utf-8")))
            if callback is not None:
                callback(part_num, False)               # 如果上传成功，需要回调通知
                raise e

        dict_etag = dict()
        dict_etag['ETag'] = dict_response['ETag'].strip('"')
        dict_etag['PartNumber'] = part_num
        self._multipart_upload['Part'].append(dict_etag)

        if callback is not None:
            callback(part_num, True)

        return dict_response           # xxx

    def complete_upload(self):
        # 首先，对multipart进行排序
        self._multipart_upload['Part'] = sorted(self._multipart_upload['Part'], key=lambda part: part["PartNumber"])

        try:
            dict_response = self._cos_client.complete_multipart_upload(Bucket=self._bucket_name,
                                                                       Key=self._key_name,
                                                                       UploadId=self._upload_id,
                                                                       MultipartUpload=self._multipart_upload)
        except CosException as e:
            logger.exception("Complete multipart upload occurs a CosException. "
                             "File:{0}, UploadId:{1}. Thread:{2}".format(str(self._key_name).encode("utf-8"),
                                                                               str(self._upload_id).encode("utf-8"),
                                                                               str(threading.current_thread().getName()).encode("utf-8")))
            raise e
        except Exception as e:
            logger.exception("Complete multipart upload occurs a exception. "
                             "File:{0}, UploadId:{1}. Thread:{2}".format(str(self._key_name).encode("utf-8"),
                                                                               str(self._upload_id).encode("utf-8"),
                                                                               str(threading.current_thread().getName()).encode("utf-8")))
            logger.error("Complete upload failed. File:{0} Thread:{1}".format(self._key_name, threading.currentThread().getName()))
            raise e
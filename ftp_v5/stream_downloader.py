# -*- coding:utf-8 -*-

import logging
import math
from os import read
import threading
import time

from pyftpdlib.filesystems import FilesystemError
from qcloud_cos.cos_exception import CosClientError
from cStringIO import StringIO

import ftp_v5.conf.common_config
from ftp_v5.conf.ftp_config import CosFtpConfig
from ftp_v5.multipart_upload import MultipartUpload
from ftp_v5 import utils
from qcloud_cos import CosServiceError

logger = utils.get_ftp_logger(__name__)


class StreamDownloader(object):

    _lock = threading.Lock()

    def __init__(self, cos_client, bucket_name, object_name=None):
        self._cos_client = cos_client
        self._bucket_name = bucket_name
        self._key_name = object_name

        self._is_resume_first_read = False
        self._offset = 0
        self._first_read = True
        self._bytes_read = 0

        response = self._cos_client.head_object(Bucket=self._bucket_name, Key=self._key_name)
        self._content_length = response['Content-Length']


    def read(self, size=-1):
        logger.debug("reading from ftp, bucket: {}, object key: {}, resume offset: {}, read size:{} "\
            .format(self._bucket_name, self._key_name, self._offset, size))
        # 首次read，用sdk发起请求，记录流对象，以后每次都从对象中 read
        if self._first_read or self._is_resume_first_read:
            # 处理 offset 大于等于 content-length 的情况
            if int(self._offset) >= int(self._content_length):
                logger.debug('in fitst read, offset:{}, content-length:{}'.format(self._offset, self._content_length))
                return ''
            response = self._cos_client.get_object(
                Bucket=self._bucket_name,
                Key=self._key_name,
                Range='bytes={}-{}'.format(self._offset, self._content_length)
            )
            self._buffer = response['Body']
            self._first_read = False
            self._is_resume_first_read = False
        self._bytes_read += size
        return self._buffer.read(size)


    def seek(self, offset, whence=0):
        logger.debug("initiate file seek, file = {}, offset = {}".format(self._key_name, offset))
        if offset > self._content_length or offset < 0:
            logger.error("offset:{} illegal, object content-length:{}".format(offset, self._content_length))
            raise FilesystemError("Seek failed. File:{}".format(self._key_name))
        if whence == 0:
            self._offset = offset
        elif whence == 1:
            self._offset = self._bytes_read + offset
            self._bytes_read = self._offset
        elif whence == 2:
            self._offset = self._content_length - offset
        else:
            logger.error("in file seek, whence illegal, whence = {}".format(whence))
            raise FilesystemError("seeking file illegal: whence = {} (do not support seeking from current position)".format(whence))
        # 设置标志位，seek之后再次read，重新打开文件对象
        self._is_resume_first_read = True


    def tell(self):
        logger.debug("initiate file tell, file = {}, _bytes_read = {}".format(self._bytes_read))
        return self._bytes_read


    def close(self):
        logger.info(
            "Closing the stream download... File: {}".format(self._key_name))


if __name__ == "__main__":
    pass

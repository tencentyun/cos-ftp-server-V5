# -*- coding:utf-8 -*-

import logging
import math
import threading
from cStringIO import StringIO
import ftp_v5.conf.common_config
from ftp_v5.conf.ftp_config import CosFtpConfig
from ftp_v5.multipart_upload import MultipartUpload
from ftp_v5.upload_pool import UploadPool


class FifoBuffer(object):
    def __init__(self, fixed_buf_len):
        self._fixed_buf_len = fixed_buf_len
        self._buf = bytearray()

    def read(self, read_len):
        read_buf = self._buf[:read_len]
        del self.buf[:read_len]
        return str(read_buf)

    def write(self, data):
        if len(self.buf) + len(data) > self._fixed_buf_len:
            raise IOError("buf is full")

        self.buf.extend(data)


    def close(self):
        del self.buf[:]

logger = logging.getLogger(__name__)

class StreamUploader(object):

    MIN_PART_SIZE = CosFtpConfig().min_part_size
    MAX_PART_SIZE = 5 * ftp_v5.conf.common_config.GIGABYTE
    UPLOAD_THREAD_NUM = CosFtpConfig().upload_thread_num

    def __init__(self, cos_client, bucket_name, object_name=None):
        self._cos_client = cos_client
        self._bucket_name = bucket_name
        self._key_name = object_name

        if CosFtpConfig().single_file_max_size > 40 * 1000 * ftp_v5.conf.common_config.GIGABYTE:
            raise ValueError("File size: %d is too big" % CosFtpConfig().single_file_max_size)

        self._min_part_size = int(math.ceil(float(CosFtpConfig().single_file_max_size) / MultipartUpload.MaxiumPartNum));

        if self._min_part_size < StreamUploader.MIN_PART_SIZE:
            self._min_part_size = StreamUploader.MIN_PART_SIZE              # part size 最小限制为1MB

        logger.info("Min part size: %d" % self._min_part_size)

        self._has_init = False
        self._has_commit = False
        self._buffer = FifoBuffer(self._min_part_size + 1 * ftp_v5.conf.common_config.MEGABYTE)
        self._buffer_len = 0
        self._multipart_uploader = None
        self._part_num = 1
        self._uploaded_len = 0                                                      # 已经上传字节数
        self._upload_pool = None

    def _wait_for_finish(self):
        self._notify_semaphore.acquire()
        if not self._isSuccesss:
            raise IOError("Uploading file failed!")
        else:
            self._part_num += 1
            self._uploaded_len += self._min_part_size
            self._isSuccesss = False

    def write(self, data):
        logger.debug("Receive string with length : {0}".format(len(data)))

        self._buffer_len += len(data)

        if self._uploaded_len > CosFtpConfig().single_file_max_size:
            logger.error("Uploading file exceeds the maximum file limit: {0}".format( str(CosFtpConfig().single_file_max_size).encode("utf-8") ) )
            raise IOError( "Uploading file exceeds the maximum file limit: {0}".format( str(CosFtpConfig().single_file_max_size).encode("utf-8") ) )

        while self._buffer_len >= self._min_part_size:
            if not self._has_init:
                self._upload_pool = UploadPool()
                response = self._cos_client.create_multipart_upload(Bucket=self._bucket_name, Key=self._key_name)
                self._multipart_uploader = MultipartUpload(self._cos_client, response)
                self._part_num = 0
                self._notify_semaphore = threading.Semaphore(1)
                self._uploaded_len -= self._min_part_size
                self._isSuccesss = True
                self._has_init = True

            def upload_callback(isSuccess):
                self._isSuccesss = isSuccess
                self._notify_semaphore.release()

            self._wait_for_finish()
            self._upload_pool.apply_task(self._multipart_uploader.upload_part, (StringIO(self._buffer.read(self._min_part_size)), self._next_part), callback=upload_callback)

            self._buffer_len -= self._min_part_size                        # 只要提交到并发上传的线程池中，就可以减掉了

            logger.info("upload new part with length: {0}".format(self._min_part_size))

    def close(self):
        logger.info("Closing the stream upload...")

        if self._buffer_len != 0:
            if not self._has_init:
                # 采用简单文件上传
                logger.info("Simple file upload!")
                self._cos_client.put_object(Bucket=self._bucket_name,
                                            Body=self._buffer.read(self._buffer_len),
                                            Key=self._key_name)
            else:
                self._wait_for_finish()
                self._multipart_uploader.upload_part(StringIO(self._buffer.read(self._min_part_size)), self._part_num)

        if self._has_init:
            self._upload_pool.close()
            self._multipart_uploader.complete_upload()

        self._uploaded_len = 0
        self._buffer.close()


if __name__ == "__main__":
    pass

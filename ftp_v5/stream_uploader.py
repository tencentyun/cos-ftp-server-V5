# -*- coding:utf-8 -*-

import logging
import math
import threading
import time
from cStringIO import StringIO

import ftp_v5.conf.common_config
from ftp_v5.conf.ftp_config import CosFtpConfig
from ftp_v5.multipart_upload import MultipartUpload
from ftp_v5.upload_pool import UploadPool

logger = logging.getLogger(__name__)


class FifoBuffer(object):
    def __init__(self):
        logger.info("Init a buf. Thread: %s" % threading.currentThread().getName())
        self._cur_read_pos = 0
        self._cur_write_pos = 0
        self._buf = StringIO()

    def read(self, read_len):
        self._buf.seek(self._cur_read_pos)                                          # 先定位文件指针到当前读指针的位置
        read_buf = self._buf.read(read_len)                                         # 读出内容
        last_content = self._buf.read(self._cur_write_pos - self._buf.tell())       # 读出尾部的东西
        self._buf.seek(0)
        self._buf.write(last_content)                                               # 将尾部拷贝到前面
        self._cur_write_pos = self._buf.tell()
        self._cur_read_pos = 0
        return read_buf

    def write(self, data):
        self._buf.seek(self._cur_write_pos)
        self._buf.write(data)
        self._cur_write_pos = self._buf.tell()

    def close(self):
        self._buf.seek(0, 2)
        logger.info("Closing buf, size:%d. Thread: %s" % (self._buf.tell(), threading.currentThread()))
        self._buf.close()
        del self._buf


class StreamUploader(object):

    MIN_PART_SIZE = CosFtpConfig().min_part_size
    MAX_PART_SIZE = 5 * ftp_v5.conf.common_config.GIGABYTE
    UPLOAD_THREAD_NUM = CosFtpConfig().upload_thread_num

    _lock = threading.Lock()

    def __init__(self, cos_client, bucket_name, object_name=None):
        self._cos_client = cos_client
        self._bucket_name = bucket_name
        self._key_name = object_name

        if CosFtpConfig().single_file_max_size > 40 * 1000 * ftp_v5.conf.common_config.GIGABYTE:
            logger.error("Max file size: %d is too big. Thread: %s" % (CosFtpConfig().single_file_max_size, threading.currentThread().getName()))
            raise ValueError("Max file size: %d is too big" % CosFtpConfig().single_file_max_size)

        self._min_part_size = int(math.ceil(float(CosFtpConfig().single_file_max_size) / MultipartUpload.MaxiumPartNum))

        if self._min_part_size < StreamUploader.MIN_PART_SIZE:
            self._min_part_size = StreamUploader.MIN_PART_SIZE                      # part size 最小限制为1MB

        logger.info("Min part size: %d" % self._min_part_size)

        self._has_init = False
        self._has_commit = False
        self._buffer = FifoBuffer()
        self._buffer_len = 0
        self._multipart_uploader = None
        self._part_num = 1                                                          # 当前上传的分片号
        self._uploaded_part = dict()                                                # 已经成功上传的分片
        self._uploaded_len = 0                                                      # 已经上传字节数
        self._upload_pool = None                                                    # 用于并发上传的线程池子

    def write(self, data):

        self._buffer.write(data)
        self._buffer_len += len(data)

        if self._uploaded_len > CosFtpConfig().single_file_max_size:
            logger.error("Uploading file: {0} exceeds the maximum file limit: {1}".format(self._key_name, str(CosFtpConfig().single_file_max_size).encode("utf-8")))
            raise IOError("Uploading file: {0} exceeds the maximum file limit: {1}".format(self._key_name, str(CosFtpConfig().single_file_max_size).encode("utf-8")))

        while self._buffer_len >= self._min_part_size:
            if not self._has_init:
                self._upload_pool = UploadPool()
                response = self._cos_client.create_multipart_upload(Bucket=self._bucket_name, Key=self._key_name)
                self._multipart_uploader = MultipartUpload(self._cos_client, response)
                self._part_num = 1
                self._isSuccess = None
                self._has_init = True

            def callback(part_num, result):
                with StreamUploader._lock:
                    self._uploaded_part[str(part_num)] = result
                    self._isSuccess = result

            def check_finish():
                if self._isSuccess is not None and not self._isSuccess:
                    err_msg = "Uploading file:{0} failed.".format(self._key_name)
                    logger.error(err_msg)
                    raise IOError(err_msg)

            check_finish()
            self._uploaded_part[str(self._part_num)] = None
            self._upload_pool.apply_task(self._multipart_uploader.upload_part, (self._buffer.read(self._min_part_size), self._part_num, callback))

            self._part_num += 1
            self._buffer_len -= self._min_part_size                        # 只要提交到并发上传的线程池中，就可以减掉了
            self._uploaded_len += self._min_part_size

            logger.info("upload new part with length: {0} File: {1}".format(self._min_part_size, self._key_name))

    def _wait_for_finish(self):
        is_finish = False
        while not is_finish:
            if len(self._uploaded_part) == 0:
                return
            for part_num, result in self._uploaded_part.items():
                if result is not None and  not result:
                    logger.error("Uploading file failed. Failed part_num: %d " % int(part_num))
                    raise IOError("Uploading part_num: %d failed. " % int(part_num))
                if result is None:
                    break
            else:
                is_finish = True
            if not is_finish:
                time.sleep(10 / 1000)                                        # 休眠10毫秒

    def close(self):
        logger.info("Closing the stream upload... File: %s, Thread:%s".format(self._key_name, threading.currentThread()))

        if self._buffer_len != 0:
            if not self._has_init:
                # 采用简单文件上传
                logger.info("Simple file upload! File: {0}".format(self._key_name))
                self._cos_client.put_object(Bucket=self._bucket_name,
                                            Body=self._buffer.read(self._buffer_len),
                                            Key=self._key_name)
            else:
                logger.info("Upload the last part File：{0}".format(self._key_name))
                self._multipart_uploader.upload_part(self._buffer.read(self._buffer_len), self._part_num)

        if self._has_init:
            logger.info("Wait for all the tasks to finish.")
            self._wait_for_finish()
            self._multipart_uploader.complete_upload()

        self._uploaded_len = 0
        self._buffer.close()

if __name__ == "__main__":
    pass

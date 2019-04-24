# -*- coding:utf-8 -*-

import logging
import threading

from ftp_v5.conf.ftp_config import CosFtpConfig

logger = logging.getLogger(__name__)


class UploadThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, callback=None):
        threading.Thread.__init__(self, group=group, target=target, name=name, args=args, kwargs=kwargs)
        self.__callback = callback

    def run(self):
        super(UploadThread, self).run()
        self.__callback()


class UploadPool(object):
    _instance = None
    _isInit = False
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(UploadPool, cls).__new__(cls)
            return cls._instance

    def __init__(self):
        if UploadPool._isInit:  # 如果已经初始化就不再初始化了
            return

        logger.info("init pool")
        self._thread_num = CosFtpConfig().upload_thread_num  # 线程数目
        self._semaphore = threading.Semaphore(CosFtpConfig().upload_thread_num)  # 控制线程数目
        self._reference_threads = set()  # 引用计数
        UploadPool._isInit = True

    def apply_task(self, func, args=(), kwds={}):
        self._semaphore.acquire()
        UploadThread(target=func, args=args, kwargs=kwds, callback=self.release).start()

    def release(self):
        logger.info("Thread {0} release the semaphore.".format(threading.currentThread().getName()))
        self._semaphore.release()

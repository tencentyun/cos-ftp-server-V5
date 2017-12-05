# -*- coding:utf-8 -*-

from multiprocessing.pool import ThreadPool
from ftp_v5.conf.ftp_config import CosFtpConfig
import threading
import logging
logger = logging.getLogger(__name__)


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
        if UploadPool._isInit:                                                           # 如果已经初始化就不再初始化了
            return

        logger.info("init pool")
        self._thread_pool = ThreadPool(CosFtpConfig().upload_thread_num)                  # 固定线程池的大小
        self._thread_num = CosFtpConfig().upload_thread_num                               # 线程数目
        self._semaphore = threading.Semaphore(CosFtpConfig().upload_thread_num)           # 控制线程数目
        self._reference_threads = set()                                                   # 引用计数
        UploadPool._isInit = True

    def apply_task(self, func, args=(), kwds={}):
        self._semaphore.acquire()
        self._thread_pool.apply_async(func=func, args=args, kwds=kwds, callback=self.release)

    def release(self, args):
        logger.info("Thread {0} release the semaphore.".format(threading.currentThread().getName()))
        self._semaphore.release()

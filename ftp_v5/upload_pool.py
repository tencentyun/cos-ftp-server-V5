# -*- coding:utf-8 -*-

from multiprocessing.pool import ThreadPool
from ftp_v5.conf.ftp_config import CosFtpConfig
import Queue
import threading


class UploadPool(object):
    _instance = None

    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(UploadPool, cls).__new__(cls)
            return cls._instance

    def __init__(self):
        self._thread_pool = ThreadPool(processes=CosFtpConfig().upload_thread_num)        # 固定线程池的大小
        self._thread_num = CosFtpConfig().upload_thread_num                               # 线程数目
        self._semaphore = threading.Semaphore(CosFtpConfig().upload_thread_num)           # 控制线程数目
        self._reference_threads = set()                                                   # 引用计数

    def apply_task(self, func, args=(), kwds={}):
        with UploadPool._lock:
            self._reference_threads.add(threading.currentThread().getName())
            self._semaphore.acquire()
            self._thread_pool.apply_async(func=func, args=args, kwds=kwds, callback=self.release)

    def release(self, args):
        self._semaphore.release()

    def close(self, force=False):
        if not force and len(self._reference_threads) > 0:
            self._reference_threads.remove(threading.currentThread().getName())
            return
        self.thread_pool.close()
        self.thread_pool.join()
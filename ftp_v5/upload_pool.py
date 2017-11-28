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
        self._thread_pool = ThreadPool(processes=CosFtpConfig().upload_thread_num)
        self._thread_num = CosFtpConfig().upload_thread_num
        self._reference_threads = set()                         # 引用计数

    def apply_task(self, func, args=(), kwds={}, callback=None):
        with UploadPool._lock:
            self._reference_threads.add(threading.currentThread().getName())
            if self._thread_num > 1:
                self._thread_pool.apply_async(func=func, args=args, kwds=kwds)
                self._thread_num -= 1
                return
            self._thread_pool.apply(func=func, args=args, kwds=kwds)
            self._thread_num = CosFtpConfig().upload_thread_num

    def close(self, force=False):
        if not force and len(self._reference_threads) > 0:
            self._reference_threads.remove(threading.currentThread().getName())
            return

        self.thread_pool.close()
        self.thread_pool.join()
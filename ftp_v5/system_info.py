# -*- coding:utf-8 -*-
import psutil


def get_total_memory():
    sys_memory = psutil.virtual_memory()
    return sys_memory.total


def get_used_memory():
    sys_memory = psutil.virtual_memory()
    return sys_memory.used


def get_available_memory():
    sys_memory = psutil.virtual_memory()
    return sys_memory.available

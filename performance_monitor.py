#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Author: leeyoshinari
# Monitoring
import os
import time
import traceback
import config as cfg
from logger import logger
from extern import ports_to_pids


class PerMon(object):
    def __init__(self):
        self._is_run = 0
        self._pid = []
        self._port = []
        self.db = None
        self.cursor = None
        self._total_time = 66666666
        self.interval = int(cfg.INTERVAL)
        self.disk = cfg.DISK

        self.cpu_cores = 0  # CPU core number
        self.total_mem = 0  # total memory

        self.get_cpu_cores()
        self.get_total_mem()

        self.start_time = 0

    @property
    def is_run(self):
        return self._is_run

    @is_run.setter
    def is_run(self, value):
        self._is_run = value

    @property
    def pid(self):
        return self._pid

    @pid.setter
    def pid(self, value):
        self._pid = value

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value):
        self._port = value

    @property
    def total_time(self):
        return self._total_time

    @total_time.setter
    def total_time(self, value):
        if value:
            self._total_time = value + 60

    def write_cpu_mem(self):
        """
        Monitoring CPU and memory.
        """
        while True:
            if self._is_run == 1:
                self.start_time = time.time()
                start_search_time = time.time()

                while True:
                    if time.time() - self.start_time < self._total_time:
                        get_data_time = time.time()
                        if get_data_time - start_search_time > self.interval:
                            start_search_time = get_data_time
                            '''if self.cm_counter > cfg.RUN_ERROR_TIMES:
                                self._is_run = 0    # if the times of failure is larger than default, stop monitor.
                                logger.logger.error('Stop monitor, because commands run error.')
                                self.cm_counter = 0
                                break'''

                            try:
                                for pid in self._pid:
                                    cpu, mem = self.get_cpu(pid)
                                    if cpu is None:
                                        continue

                                    jvm = self.get_mem(pid)

                                    logger.logger.info(f'cpu_and_mem: {pid},{cpu},{mem},{jvm}')

                            except Exception as err:
                                logger.logger.error(traceback.format_exc())
                                time.sleep(cfg.SLEEPTIME)

                                pid_transfor = ports_to_pids(self._port)
                                if pid_transfor:
                                    if isinstance(pid_transfor, str):
                                        logger.logger.error(f'The pid of {pid_transfor} is not existed.')
                                    elif isinstance(pid_transfor, list):
                                        self._pid = pid_transfor

                                continue

                    else:
                        self._is_run = 0    # if the total time is up, stop monitor.
                        logger.logger.info('Stop monitor, because total time is up.')
                        break

                    if self._is_run == 0:   # if _is_run=0, stop monitor.
                        logger.logger.info('Stop monitor.')
                        break
            else:
                time.sleep(cfg.SLEEPTIME)

    def write_io(self):
        while True:
            if self._is_run == 1:
                self.start_time = time.time()

                while True:
                    if time.time() - self.start_time < self._total_time:
                        '''if self.io_counter > cfg.RUN_ERROR_TIMES:
                            self._is_run = 0
                            logger.logger.error('Stop monitor, because commands run error.')
                            self.io_counter = 0
                            break'''

                        try:
                            for ipid in self._pid:
                                ioer = self.get_io(ipid)

                                logger.logger.info(f'r_w_util: {ipid},{ioer[0]},{ioer[1]},{ioer[-1]},{ioer[2]},{ioer[3]},{ioer[4]}')

                        except Exception as err:
                            logger.logger.error(traceback.format_exc())
                            time.sleep(cfg.SLEEPTIME)
                            continue

                    else:
                        self._is_run = 0
                        logger.logger.info('Stop monitor, because total time is up.')
                        break

                    if self._is_run == 0:
                        # logger.logger.info('Stop monitor.')
                        break
            else:
                time.sleep(cfg.SLEEPTIME)

    def write_handle(self):
        while True:
            if self._is_run == 1:
                self.start_time = time.time()

                while True:
                    if time.time() - self.start_time < self._total_time:
                        '''if self.handle_counter > cfg.RUN_ERROR_TIMES:
                            logger.logger.error('Stop monitor, because commands run error.')
                            self._is_run = 0
                            self.handle_counter = 0
                            break'''

                        try:
                            for hpid in self._pid:
                                handles = self.get_handle(hpid)
                                if handles is None:
                                    continue

                                logger.logger.info(f'handles: {hpid},{handles}')

                        except Exception as err:
                            logger.logger.info(traceback.format_exc())
                            time.sleep(cfg.SLEEPTIME)
                            continue

                    else:
                        self._is_run = 0
                        logger.logger.info('Stop monitor, because total time is up.')
                        break

                    if self._is_run == 0:
                        # logger.logger.info('Stop monitor.')
                        break
            else:
                time.sleep(cfg.SLEEPTIME)

    def get_cpu(self, pid):
        """
        Get CPU and Memory of specified PID. It uses `top`.
        It returns CPU(%), and Memory(G).
        """
        result = os.popen(f'top -n 1 -b -p {pid} |tr -s " "').readlines()[-1]
        res = result.strip().split(' ')
        logger.logger.debug(res)

        cpu = None
        mem = None
        if str(pid) in res:
            ind = res.index(str(pid))
            cpu = float(res[ind + 8]) / self.cpu_cores
            mem = float(res[ind + 9]) * self.total_mem

        return cpu, mem

    @staticmethod
    def get_mem(pid):
        """
        Get JVM of specified PID. It uese `jstat`.
        It returns JVM(G).
        """
        mem = 0
        try:
            result = os.popen(f'jstat -gc {pid} |tr -s " "').readlines()[1]
            res = result.strip().split(' ')
            logger.logger.debug(res)
            mem = float(res[2]) + float(res[3]) + float(res[5]) + float(res[7])
        except Exception as err:
            logger.logger.info(err)

        return mem / 1024 / 1024

    def get_io(self, pid):
        """
        Get IO of specified PID. It uses `iotop`.
        It returns IO(%).
        """
        # get rkB/s and wkB/s.
        result = os.popen(f'iotop -n 2 -d 1 -b -qqq -p {pid} -k |tr -s " "').readlines()[-1]
        res = result.strip().split(' ')
        logger.logger.debug(res)

        disk_r, disk_w, disk_util = self.get_disk_io()

        writer = None
        reader = None
        if str(pid) in res:
            ind = res.index(str(pid))
            writer = float(res[ind + 3])
            reader = float(res[ind + 5])

        # IO of PID
        try:
            ratio_w = writer / disk_w * disk_util
        except Exception as err:
            logger.logger.warning(err)
            ratio_w = 0

        try:
            ratio_r = reader / disk_r * disk_util
        except Exception as err:
            logger.logger.warning(err)
            ratio_r = 0

        return [reader, writer, disk_r, disk_w, disk_util, max(ratio_r, ratio_w)]

    def get_disk_io(self):
        """
        Get IO of disk. It uses `iostat`.
        It returns disk_r(kB/s), disk_w(kB/s) and disk_util(%).
        """
        disk_r = None
        disk_w = None
        disk_util = None
        try:
            result = os.popen('iostat -d -x -k {} 1 2 |tr -s " "'.format(self.disk)).readlines()
            res = [line for line in result if self.disk in line]
            disk_res = res[-1].strip().split(' ')
            logger.logger.debug(disk_res)

            if self.disk in disk_res:
                disk_r = float(disk_res[5])
                disk_w = float(disk_res[6])
                disk_util = float(disk_res[-1])

        except Exception as err:
            logger.logger.error(err)

        return disk_r, disk_w, disk_util

    @staticmethod
    def get_handle(pid):
        """
        Get handles of specified PID. It uses `lsof`.
        It returns handles number.
        """
        result = os.popen("lsof -n | awk '{print $2}'| sort | uniq -c | sort -nr | " + "grep {}".format(pid)).readlines()
        res = result[0].strip().split(' ')
        logger.logger.debug(res)
        handles = None
        if str(pid) in res:
            handles = int(res[0])

        return handles

    def get_cpu_cores(self):
        """
        Get CPU core number.
        """
        result = os.popen('cat /proc/cpuinfo| grep "processor"| wc -l').readlines()[0]

        self.cpu_cores = int(result)

        logger.logger.info(f'CPU core number is {self.cpu_cores}')

    def get_total_mem(self):
        """
        Ger total memory.
        """
        result = os.popen('cat /proc/meminfo| grep "MemTotal"| uniq').readlines()[0]

        self.total_mem = float(result.split(':')[-1].split('k')[0].strip()) / 1024 / 1024 / 100

        logger.logger.info(f'Total memory is {self.total_mem * 100}')

    def __del__(self):
        pass

#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Author: leeyoshinari

# server
IP = '127.0.0.1'
PORT = '5555'

# MySQL server
MySQL_IP = '127.0.0.1'
MySQL_PORT = '3306'
MySQL_USERNAME = 'root'
MySQL_PASSWORD = '123456'
MySQL_DATABASE = 'performance_monitor'

# monitor config
INTERVAL = 0
RUN_ERROR_TIMES = 10    # The number of times the commands failed to run when monitoring.
SLEEPTIME = 3   # Polling interval, when stopping monitor, polling to start monitor when satisfying condition.
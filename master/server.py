#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: leeyoshinari
import os
import time
import json
import asyncio
import traceback
import jinja2
import aiohttp_jinja2
from aiohttp import web

from logger import logger, cfg
from process import Process
from Email import sendEmail
from request import Request
from draw_performance import draw_data_from_db


master = Process()
http = Request()


async def index(request):
	"""
	首页，浏览器访问 http://ip:port
	:param request:
	:return:
	"""
	return aiohttp_jinja2.render_template('home.html', request, context={
		'ip': master.slaves['ip'], 'port': master.slaves['port'], 'system': master.slaves['system'],
		'cpu': master.slaves['cpu'], 'mem': master.slaves['mem'], 'time': master.slaves['time']})


async def start_monitor(request):
	"""
	开始监控页面
	:param request:
	:return:
	"""
	monitor_list = master.get_monitor()
	return aiohttp_jinja2.render_template('runMonitor.html', request, context={
		'ip': master.slaves['ip'], 'foos': monitor_list, 'run_status': ['已停止', '监控中', '排队中']})


async def visualize(request):
	"""
	监控结果可视化页面
	:param request:
	:return:
	"""
	starttime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()-3600))
	endtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
	# 防止未监控时，访问页面报错
	if master.slaves['ip']:
		monitor_list = master.get_monitor(host=master.slaves['ip'][0])
	else:
		monitor_list = {'port': []}
	return aiohttp_jinja2.render_template('visualize.html', request, context={'disks': master.slaves['disk'],
		'ip': master.slaves['ip'], 'port': monitor_list['port'], 'starttime': starttime, 'endtime': endtime})


async def registers(request):
	"""
	注册接口
	:param request:
	:return:
	"""
	data = await request.json()
	logger.debug(f'注册接口请求参数为{data}')
	host = data.get('host')     # 客户端服务器IP
	port = data.get('port')     # 客户端启用的端口号
	system = data.get('system')
	cpu = data.get('cpu')
	mem = data.get('mem')
	nic = data.get('nic')
	disks = data.get('disks')   # 客户端服务器磁盘号
	master.slaves = {
		'host': host,
		'port': port,
		'system': system,
		'cpu': cpu,
		'mem': mem,
		'disk': disks,
		'nic': nic,
		'time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
	}
	return web.json_response({'code': 0, 'msg': '注册成功!', 'data': None})


async def run_monitor(request):
	"""
	开始/停止监控接口
	:param request:
	:return:
	"""
	try:
		data = await request.post()
		logger.debug(f'监控接口请求参数为{data}')
		host = data.get('host')     # 待监控的服务器IP
		port = data.get('port')     # 待监控的端口号
		is_run = data.get('isRun')  # 是否开始监控，0为停止监控，1为开始监控
		post_data = {
			'host': host,
			'port': port,
			'isRun': is_run
		}
		ind = master.slaves['ip'].index(host)
		res = http.request('post', host, master.slaves['port'][ind], 'runMonitor', json=post_data)    # 请求接口

		if res.status_code == 200:
			return web.Response(body=res.content.decode())
		else:
			return web.json_response({'code': 2, 'msg': f"系统异常，消息来自{host}", 'data': None})

	except Exception as err:
		logger.error(err)
		return web.json_response({'code': 2, 'msg': '系统异常',	'data': None})


async def get_monitor(request):
	"""
	获取监控端口列表接口
	:param request:
	:return:
	"""
	ip = request.match_info['host']
	monitor_list = {'host': [], 'port': [], 'pid': [], 'isRun': [], 'startTime': []}
	try:
		port = master.slaves['port'][master.slaves['ip'].index(ip)]     # 获取端口监控列表
		post_data = {
			'host': ip,
		}
		res = http.request('post', ip, port, 'getMonitor', json=post_data)      # 通过url获取
		if res.status_code == 200:
			response = json.loads(res.content.decode())
			logger.debug(f'{ip}服务器获取监控列表接口返回值为{response}')
			if response['code'] == 0:
				# 拼接端口监控列表
				monitor_list['host'] += response['data']['host']
				monitor_list['port'] += response['data']['port']
				monitor_list['pid'] += response['data']['pid']
				monitor_list['isRun'] += response['data']['isRun']
				monitor_list['startTime'] += response['data']['startTime']

				return web.json_response({'code': 0, 'msg': '操作成功', 'data': monitor_list})
			else:   # 如果接口返回异常，则跳过
				logger.warning(f'{ip}服务器获取监控列表接口返回参数异常，异常信息{response["msg"]}')
				return web.json_response({'code': response['code'], 'msg': response["msg"], 'data': None})
		else:   # 如果接口响应异常，则跳过
			logger.warning(f'从{ip}服务器获取监控列表异常，响应状态码为{res.status_code}。')
			return web.json_response({'code': 2, 'msg': "系统异常", 'data': None})

	except Exception as err:
		logger.error(err)
		return web.json_response({'code': 2, 'msg': "系统异常", 'data': None})


async def plot_monitor(request):
	"""
	画图
	:param request:
	:return:
	"""
	data = await request.post()
	logger.debug(f'可视化接口请求参数为{data}')
	host = data.get('host')     # 客户端服务器IP
	start_time = data.get('startTime')  # 监控数据开始时间
	end_time = data.get('endTime')      # 监控数据结束时间
	type_ = data.get('type')            # 可视化类型，画端口结果还是系统结果
	port_pid = data.get('port')         # 端口号
	disk = data.get('disk')         # 磁盘号
	try:
		if type_ == 'port':
			res = draw_data_from_db(host=host, port=port_pid, start_time=start_time, end_time=end_time, disk=disk)
			if res['code'] == 0:
				raise Exception(res['message'])
			res.update(master.get_gc(host, master.slaves['port'][master.slaves['ip'].index(host)], f'getGC/{port_pid}'))
			return aiohttp_jinja2.render_template('figure.html', request, context={
				'img': res['img'], 'line75': res['line75'], 'line90': res['line90'], 'line95': res['line95'],
				'line99': res['line99'], 'ygc': res['ygc'], 'ygct': res['ygct'],
				'fgc': res['fgc'], 'fgct': res['fgct'], 'fygc': res['fygc'], 'ffgc': res['ffgc']})

		if type_ == 'pid':
			res = draw_data_from_db(host=host, pid=port_pid, start_time=start_time, end_time=end_time, disk=disk)
			if res['code'] == 0:
				raise Exception(res['message'])
			res.update(master.get_gc(host, master.slaves['port'][master.slaves['ip'].index(host)], f'getGC/{port_pid}'))
			return aiohttp_jinja2.render_template('figure.html', request, context={
					'img': res['img'], 'line75': res['line75'], 'line90': res['line90'], 'line95': res['line95'],
					'line99': res['line99'], 'ygc': res['ygc'], 'ygct': res['ygct'],
					'fgc': res['fgc'], 'fgct': res['fgct'], 'fygc': res['fygc'], 'ffgc': res['ffgc']})

		if type_ == 'system':
			res = draw_data_from_db(host=host, start_time=start_time, end_time=end_time, system=1, disk=disk)
			if res['code'] == 0:
				raise Exception(res['message'])
			return aiohttp_jinja2.render_template('figure.html', request, context={
						'img': res['img'], 'line75': res['line75'], 'line90': res['line90'], 'line95': res['line95'],
						'line99': res['line99'], 'ygc': -1, 'ygct': -1, 'fgc': -1, 'fgct': -1, 'fygc': -1, 'ffgc': -1})

	except Exception as err:
		logger.error(err)
		return aiohttp_jinja2.render_template('warn.html', request, context={'msg': err})


async def get_port_disk(request):
	"""
	根据服务器IP获取对应服务器的所有磁盘号和所以已监控得端口号
	:param request:
	:return:
	"""
	host = request.match_info['host']
	if host in master.slaves['ip']:
		try:
			disks = master.slaves['disk'][master.slaves['ip'].index(host)]
			monitor_list = master.get_monitor(host=host)
			return web.json_response({'code': 0, 'msg': '操作成功', 'data': {'disk': disks, 'port': monitor_list['port']}})
		except Exception as err:
			logger.error(err)
			return web.json_response({'code': 2, 'msg': "系统异常", 'data': None})
	else:
		return web.json_response({'code': 1, 'msg': f"{host}未注册", 'data': None})


async def notice(request):
	"""
	发送邮件
	:param request:
	:return:
	"""
	data = await request.json()
	msg = data.get('msg')
	sendEmail(msg)
	return web.json_response({'code': 0, 'msg': '操作成功', 'data': None})


async def main():
	app = web.Application()
	aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'))  # 将模板添加到搜索路径
	app.router.add_static('/static/', path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'))  # 将静态文件添加到搜索路径

	app.router.add_route('GET', '/', index)
	app.router.add_route('GET', '/startMonitor', start_monitor)
	app.router.add_route('GET', '/getMonitor/{host}', get_monitor)
	app.router.add_route('GET', '/Visualize', visualize)
	app.router.add_route('GET', '/getPortAndDisk/{host}', get_port_disk)

	app.router.add_route('POST', '/Register', registers)
	app.router.add_route('POST', '/runMonitor', run_monitor)
	app.router.add_route('POST', '/plotMonitor', plot_monitor)
	app.router.add_route('POST', '/Notification', notice)

	runner = web.AppRunner(app)
	await runner.setup()
	site = web.TCPSite(runner, cfg.getServer('host'), cfg.getServer('port'))
	await site.start()


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.run_forever()

# -*- coding:utf-8 -*-
# @Time        : 20.1.18 18:09
# @Author      : liyihang@corp.netease.com
# @File        : Client.py
# @Description : 前提, 网络都已经建立好了
import socket
import time

from RpcCommon import RpcMethod, Proxy, RpcChannel, EntityService


class ClientGlobal(object):
	"""全局"""
	CONNECT = None
	ENTITY_MANAGER = {}  # 简略实现


class ClientService(EntityService):
	def GetEntity(self, entityID):
		return ClientGlobal.ENTITY_MANAGER.get(entityID)


class ClientHost(object):
	def __init__(self):
		self.sock = socket.socket()
		self.channel = RpcChannel(self.sock)
		self.channel.SetService(ClientService())
		self.Connect()

	def Connect(self):
		self.sock.connect(("127.0.0.1", 6666))


class ClientAvatar(object):
	def __init__(self, entityID, channel):
		self.id = entityID
		self.server = Proxy(entityID, channel)

	@RpcMethod
	def ClientEcho(self, *args, **kwargs):
		print "args", args
		print "kwargs", kwargs


if __name__ == '__main__':
	# net init
	ClientGlobal.CONNECT = ClientHost()

	# 一个连接对应一个avatar, 实际上会复杂很多
	ca = ClientAvatar(0, ClientGlobal.CONNECT.channel)
	ClientGlobal.ENTITY_MANAGER[0] = ca

	# test case
	ca.server.ServerEcho("I'm Client", time=time.time(), name="client")  # 先发一次
	while True:
		try:
			ClientGlobal.CONNECT.channel.Recv()
			time.sleep(0.1)
		except socket.error:
			ClientGlobal.CONNECT.channel.Close()
	# except:
	# 	print "Client Close"
	# 	exit(0)

# -*- coding:utf-8 -*-
# @Time        : 20.1.18 21:14
# @Author      : liyihang@corp.netease.com
# @File        : Server.py
# @Description :
import time

from RpcCommon import RpcChannel, RpcMethod, Proxy, EntityService
import socket
import thread


class ServerGlobal(object):
	RPC_SERVICE = None
	ENTITY_MANAGER = {}  # 简略实现


class SeverService(EntityService):
	def GetEntity(self, entityID):
		return ServerGlobal.ENTITY_MANAGER.get(entityID)


class ServerHost(object):
	def __init__(self):
		self.sock = socket.socket()
		self.channels = []

	def Start(self):
		self.sock.bind(("0.0.0.0", 6666))
		self.sock.listen(5)
		try:
			while True:
				conn, peerName = self.sock.accept()
				thread.start_new_thread(self.HandleConn, (conn,))
		except:
			print "Server Close"
			exit(0)

	def HandleConn(self, conn):
		serverChannel = RpcChannel(conn)
		serverChannel.SetService(ServerGlobal.RPC_SERVICE)  # 注入
		self.channels.append(serverChannel)  # server host 管理channel

		# 一个连接对应一个avatar, 实际上会复杂很多
		ServerGlobal.ENTITY_MANAGER[0] = ServerAvatar(0, serverChannel)

		while True:
			try:
				serverChannel.Recv()  # 先收一次
				time.sleep(0.1)
			except socket.error:
				serverChannel.Close()


class ServerAvatar(object):
	def __init__(self, entityID, channel):
		self.id = entityID
		self.client = Proxy(entityID, channel)

	@RpcMethod
	def ServerEcho(self, *args, **kwargs):
		print "args", args
		print "kwargs", kwargs
		print "---"
		# 调回去
		self.client.ClientEcho("I'm server", time=time.time(), name="server")


if __name__ == '__main__':
	ServerGlobal.RPC_SERVICE = SeverService()
	ServerHost().Start()

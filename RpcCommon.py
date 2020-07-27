# -*- coding:utf-8 -*-
# @Time        : 20.1.18 17:51
# @Author      : liyihang@corp.netease.com
# @File        : RpcCommon.py
# @Description : 两端公用

import json
import struct
from functools import partial

from google.protobuf import service

from game_pb2 import GameService_Stub, GameService


def RpcMethod(func):
	func.__rpc__ = True
	return func


def IsRPCMethod(func):
	return getattr(func, "__rpc__", False)


class Packer(object):
	@staticmethod
	def PackParm(args, kwargs):
		parm = {
			"args": args,
			"kwargs": kwargs,
		}
		return json.dumps(parm)

	@staticmethod
	def UnpackParm(data):
		return json.loads(data)


class RpcChannel(service.RpcChannel):
	"""底层网络和RPC逻辑层的中间件"""

	def __init__(self, conn):
		self.conn = conn  # 底层
		self.service = None  # 逻辑层

	def SetService(self, serviceObj):
		self.service = serviceObj

	#
	# invoker
	#
	def CallMethod(self, method_descriptor, rpc_controller, request, response_class, callback):
		"""
		逻辑rpc发起, 最终调用到底层该方法
		rpc_controller 不使用
		callback 不使用
		response_class 不使用
		"""
		index = method_descriptor.index  # 本质还是协议号, 只不过是交给protobuf管理了
		data = request.SerializeToString()
		total_len = 6 + len(data)
		# 发过去
		wholeRequest = ''.join([struct.pack("!ih", total_len, index), data])
		self.Send(wholeRequest)  # 交给底层

	#
	# be-invoker
	#
	def MethodCall(self, data):
		total_len, index = struct.unpack("!ih", data[0:6])
		service_desc = self.service.GetDescriptor()
		method_desc = service_desc.methods[index]  # 本质就是根据协议号拿到对应函数的相关信息

		request = self.service.GetRequestClass(method_desc)()
		serialized = data[6:total_len]
		request.ParseFromString(serialized)

		self.service.CallMethod(method_desc, None, request, None)  # 交给逻辑层, 这里是proto rpc框架的接口

	#
	# Sock封装
	#
	def Send(self, data):
		self.conn.send(data)

	def Recv(self):
		data = self.conn.recv(1024)  # 阻塞
		self.MethodCall(data)

	def Close(self):
		self.conn.close()


class EntityService(GameService):
	"""职责其实就是实现stub的逻辑, 和逻辑层关联"""
	def GetEntity(self, entityID):
		raise NotImplementedError

	def entity_method(self, rpc_controller, request, callback):
		entity = self.GetEntity(request.entityID)
		if not entity:
			return

		method = getattr(entity, str(request.methodName), None)
		if not method or not IsRPCMethod(method):
			print "Error RPC, name=%s" % request.methodName
			return

		parm = Packer.UnpackParm(request.parm)
		method(*parm["args"], **parm["kwargs"])


class Proxy(GameService_Stub):
	"""整个rpc底层的封装, 供逻辑层调用"""

	def __init__(self, entityID, channel):
		self.channel = channel
		self.entityID = entityID

	def entity_method(self, methodName, *args, **kwargs):
		"""在proto中定义的函数"""
		# 处理参数, id, name, args
		selfMethodDesc = self.GetDescriptor().FindMethodByName("entity_method")  # entity_method这个rpc接口的descriptor
		request = self.GetRequestClass(selfMethodDesc)()
		request.entityID = self.entityID
		request.methodName = methodName
		byteParm = Packer.PackParm(args, kwargs)
		request.parm = byteParm

		# channel发出去
		self.channel.CallMethod(selfMethodDesc, None, request, None, None)

	def __getattr__(self, name):
		"""方便调用"""
		method = super(Proxy, self).__getattribute__("entity_method")
		return partial(method, name)  # 固定methodName 参数

import socket
import threading
import time


def get_key(dict, value):
	return [k for k, v in dict.items() if v == value][0]


def startSever(sk):
	global connlist
	while True:
		print('server waiting...')
		conn, addr = sk.accept()
		conn.send
		print(addr, "connected")
		connlist[addr[0]] = conn


def constantsend():
	global connlist
	while True:
		for conn in connlist.values():
			try:
				conn.send(bytes("No reply" + '\n', encoding='utf-8'))
				print("No reply")
			except ConnectionAbortedError:
				connlist.pop(get_key(connlist, conn))
		time.sleep(1)


def init():
	global connlist
	connlist = {}


ip_port = ('132.232.88.18', 10001)
# ip_port = ('192.168.0.167', 10001)
init()
sk = socket.socket()
sk.bind(ip_port)
sk.listen(20)
t = threading.Thread(target=startSever, args=(sk,))
t.start()
t = threading.Thread(target=constantsend)
t.start()

import socket
import threading
import time



def get_ip():
	try:
		csock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		csock.connect(('8.8.8.8', 80))
		(addr, port) = csock.getsockname()
		csock.close()
		return addr
	except socket.error:
		return "127.0.0.1"


def readmsgthread(conn, addr):
	while True:
		str = conn.recv(1024)
		print(addr, " : ", bytes(str).decode('utf-8'))


def sendmsgthread(conn):
	while True:
		sendstr = input()
		conn.send(bytes(sendstr + '\n', encoding='utf-8'))


myname = socket.getfqdn(socket.gethostname())
myaddr = get_ip()
print(myname, "  ", myaddr)
ip_port = (myaddr, 10001)

sk = socket.socket()
sk.bind(ip_port)
sk.listen(5)

while True:
	print('server waiting...')
	conn, addr = sk.accept()
	print(addr)

	t = threading.Thread(target=readmsgthread, args=(conn, addr,))
	t.start()
	t = threading.Thread(target=sendmsgthread, args=(conn,))
	t.start()

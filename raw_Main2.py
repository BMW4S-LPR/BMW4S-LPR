import base64
import ctypes
import inspect
import socket
import threading
import datetime
from hyperlpr_py3 import pipline as pp
import cv2
import time
import HK_Capture as hkc

statedict = {}

SEGKEY = "---"

catch_Interval = 0  # 设置抓图间隔，单位s
timeOut = 10  # 设置抓图超时时间，单位s
IPList = ["192.168.0.101"]
hkcamList = []
NameList = []


def get_key(dict, value):
	return [k for k, v in dict.items() if v == value][0]


def sendAmsgthread(string, conn):
	global connlist
	try:
		conn.send(bytes(string + '\n', encoding='utf-8'))
	except ConnectionAbortedError:
		connlist.pop(get_key(connlist, conn))


def get_ip():
	try:
		csock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		csock.connect(('8.8.8.8', 80))
		(addr, port) = csock.getsockname()
		csock.close()
		return addr
	except socket.error:
		return "127.0.0.1"


def startSever(sk):
	global connlist
	while True:
		print('server waiting...')
		conn, addr = sk.accept()
		print(addr, "connected")
		connlist[addr[0]] = conn


myname = socket.getfqdn(socket.gethostname())
myaddr = get_ip()
print(myname, "  ", myaddr)
ip_port = (myaddr, 10001)

sk = socket.socket()
sk.bind(ip_port)
sk.listen(20)
t = threading.Thread(target=startSever, args=(sk,))
t.start()

for i in range(len(IPList)):
	IPAddress = IPList[i]
	hkcam = hkc.HKIPCam(IPAddress, 'admin2', 'hk123456')  # 相机初始化
	hkcam.NET_DVR_SetLogToFile()  # 打开日志记录
	hkcam.Change_CamZoom(20)  # 调焦距
	hkcamList += [hkcam]
	NameList += [IPAddress[IPAddress.rfind(".") + 1:]]


def init():
	global flag, usetime, pic, startcollect, recres, STATE, statedict, connlist
	statedict[0] = "准备中"
	statedict[1] = "抓图中"
	statedict[2] = "识别图像中"
	statedict[3] = "识别完成，等待间隔时间中"
	statedict[4] = "抓图超时，重启中"
	statedict[5] = "抓图失败"
	statedict[6] = "识别发生错误"
	STATE = [0 for _ in range(len(IPList))]
	recres = []
	flag = [False for _ in range(len(IPList))]
	usetime = [-1 for _ in range(len(IPList))]
	pic = [0 for _ in range(len(IPList))]
	startcollect = [False for _ in range(len(IPList))]
	connlist = {}


def _async_raise(tid, exctype):
	"""raises the exception, performs cleanup if needed"""
	tid = ctypes.c_long(tid)
	if not inspect.isclass(exctype):
		exctype = type(exctype)
	res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
	if res == 0:
		raise ValueError("invalid thread id")
	elif res != 1:
		# """if it returns a number greater than one, you're in trouble,
		# and you should call it again with exc=NULL to revert the effect"""
		ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
		raise SystemError("PyThreadState_SetAsyncExc failed")


def stop_thread(thread):
	_async_raise(thread.ident, SystemExit)


def getpic(hkcam, Name, turn):
	global flag, usetime
	usetime[turn] = hkcam.Get_JPEGpicture(Name)
	flag[turn] = True
	return usetime[turn]


init()
while True:
	global flag, usetime, pic, startcollect, recres, connlist
	for i in range(len(IPList)):
		hkcam = hkcamList[i]
		IPAddress = IPList[i]
		Name = NameList[i]
		try:
			f = open("restartlog_{}.txt".format(Name), 'a')
			STATE[i] = 1
			for conn in connlist.values():
				t = threading.Thread(target=sendAmsgthread, args=("1002" + SEGKEY + statedict[STATE[i]], conn,))
				t.start()
			t = threading.Thread(target=getpic, args=(hkcam, Name, i))
			flag[i] = False
			usetime[i] = -1
			t.start()  # 多线程开始抓取图片
			tmp = False

			if startcollect[i]:
				TIME = timeOut * 100
			else:
				TIME = 2000

			for j in range(TIME):
				time.sleep(0.01)
				if flag[i]:
					tmp = True
					break
			if not tmp:
				stop_thread(t)
				f.write("收集图片数量：")
				f.write(str(pic))
				f.write("       ")
				pic[i] = 0
				startcollect[i] = False
				f.write("开始重启时间：")
				f.write(str(datetime.datetime.now()))
				f.write("\n")

				print("超时，准备重启:")
				STATE[i] = 4
				for conn in connlist.values():
					t = threading.Thread(target=sendAmsgthread, args=("1002" + SEGKEY + statedict[STATE[i]], conn,))
					t.start()
				hkcam.Restart()
				time.sleep(10)

			if usetime[i] > 0:
				pic[i] += 1
				if not startcollect[i]:
					startcollect[i] = True
					f.write("             恢复时间：")
					f.write(str(datetime.datetime.now()))
					f.write("\n\n")

				STATE[i] = 2
				for conn in connlist.values():
					t = threading.Thread(target=sendAmsgthread, args=("1002" + SEGKEY + statedict[STATE[i]], conn,))
					t.start()
				image = cv2.imread("capture_{}.jpg".format(Name))

				for conn in connlist.values():
					f = open("capture_{}.jpg".format(Name), 'rb')
					fread = f.read()
					time.sleep(0.05)
					t = threading.Thread(target=sendAmsgthread,
										 args=('1004' + SEGKEY + base64.b64encode(fread).decode(), conn,))
					t.start()
				recres = pp.SimpleRecognizePlate(image)
				print("result:	", recres)
				print("--------------------------------")
				tmpstr = ""
				for j in range(min(3, len(recres))):
					tmpstr += recres[j][0]
					if not j == len(recres) - 1:
						tmpstr += '  '
				if tmpstr == "":
					tmpstr = "未识别出车牌"
				for conn in connlist.values():
					t = threading.Thread(target=sendAmsgthread, args=("1001" + SEGKEY + tmpstr, conn,))
					t.start()
				time.sleep(0.1)

				posstr = ""

				if len(recres) >= 1:
					reimage = image[recres[0][2][1]:recres[0][2][1] + recres[0][2][3],
							  recres[0][2][0]:recres[0][2][0] + recres[0][2][2]]

					cv2.imwrite("re_{}.jpg".format(Name), reimage)

					for conn in connlist.values():
						f = open("re_{}.jpg".format(Name), 'rb')
						fread = f.read()
						time.sleep(0.05)
						t = threading.Thread(target=sendAmsgthread,
											 args=('1005' + SEGKEY + base64.b64encode(fread).decode(), conn,))
						t.start()

				for j in range(min(1, len(recres))):
					posstr += str(recres[j][2][0]) + SEGKEY + str(recres[j][2][1]) + SEGKEY + str(
						recres[j][2][2]) + SEGKEY + str(recres[j][2][3])
				if posstr == "":
					posstr = "None" + SEGKEY + "None" + SEGKEY + "None" + SEGKEY + "None"
				for conn in connlist.values():
					t = threading.Thread(target=sendAmsgthread, args=("1003" + SEGKEY + posstr, conn,))
					t.start()
				time.sleep(0.05)

				STATE[i] = 3
				for conn in connlist.values():
					t = threading.Thread(target=sendAmsgthread, args=("1002" + SEGKEY + statedict[STATE[i]], conn,))
					t.start()
				time.sleep(0.05)
			if usetime[i] == -47:
				print("重新登录:")
				hkcam = hkc.HKIPCam(IPAddress, 'admin2', 'hk123456')
			if STATE[i] != 3:
				STATE[i] = 5
				for conn in connlist.values():
					t = threading.Thread(target=sendAmsgthread, args=("1002" + SEGKEY + statedict[STATE[i]], conn,))
					t.start()
			print("")
			f.close()
		except:
			print("识别发生错误，请稍候...\n")
			STATE[i] = 6
			for conn in connlist.values():
				t = threading.Thread(target=sendAmsgthread, args=("1002" + SEGKEY + statedict[STATE[i]], conn,))
				t.start()
	time.sleep(catch_Interval)

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
from xlutils.copy import copy
from xlrd import open_workbook

statedict = {}

SEGKEY = "---"		

catch_Interval = 0  # 设置抓图间隔，单位s
timeOut = 10  # 设置抓图超时时间，单位s
IPList = ["192.168.0.101"]		# 摄像机群的IP地址列表



hkcamList = []
NameList = []
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
		ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
		raise SystemError("PyThreadState_SetAsyncExc failed")


def stop_thread(thread):
	_async_raise(thread.ident, SystemExit)


def getpic(hkcam, Name, turn):
	global flag, usetime
	usetime[turn] = hkcam.Get_JPEGpicture(Name)
	flag[turn] = True
	return usetime[turn]

def startCollectThread(turn):
	nowtime = time.time()
	reclist = []
	pos = 0
	while True:
		global flag, usetime, pic, startcollect, recres, connlist
		i = turn
		hkcam = hkcamList[i]
		IPAddress = IPList[i]
		Name = NameList[i]
		try:
			f = open("restartlog_{}.txt".format(Name), 'a')
			STATE[i] = 1
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

				print("{}: 超时，准备重启:".format(Name))
				STATE[i] = 4
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
				image = cv2.imread("capture_{}.jpg".format(Name))

				recres = pp.SimpleRecognizePlate(image)

				print("{}: result:	{}".format(Name, recres))
				if time.time() - nowtime > 10000:
					nowtime = time.time()
					if len(recres) > 0:
						reclist += [str(time.localtime(time.time())) + " : " + str(recres)]

				# 将结果写入Excel: out.xls
				try:
					rb = open_workbook('out.xls')
					wb = copy(rb)
					wb.get_sheet(0).write(turn, 0, IPAddress)
					for j in range(pos, len(reclist)):
						wb.get_sheet(0).write(turn, j + 1, str(recres[j][0]) + " " + str(recres[j][1]) + ' ' + (" ".join(str(_) for _ in recres[j][2])))
						pos = j

					# 写入Excel数据格式：
					# IP地址	1	时间1: 识别结果1 置信度1 左上角x坐标 左上角y坐标 右下角x坐标 右下角y坐标		时间2: 识别结果2 置信度2 左上角x坐标 左上角y坐标 右下角x坐标 右下角y坐标......
					# IP地址	2	时间1: 识别结果1 置信度1 左上角x坐标 左上角y坐标 右下角x坐标 右下角y坐标		时间2: 识别结果2 置信度2 左上角x坐标 左上角y坐标 右下角x坐标 右下角y坐标......
					# ............
					wb.save('out.xls')
					print('{}: Excel写入成功'.format(Name))
				except:
					print('{}: Excel写入失败，请检查是否被占用。'.format(Name))

				print("--------------------------------")

				STATE[i] = 3
			if usetime[i] == -47:
				print("{}: 重新登录:".format(Name))
				hkcamList[turn] = hkc.HKIPCam(IPAddress, 'admin2', 'hk123456')
			if STATE[i] != 3:
				STATE[i] = 5
			print("")
			f.close()
		except:
			print("{}: 识别发生错误，请稍候...\n".format(Name))
			STATE[i] = 6
	time.sleep(catch_Interval)


init()
startCollectThread(0)

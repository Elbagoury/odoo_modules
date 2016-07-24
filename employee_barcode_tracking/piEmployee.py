import urllib, urllib2
import sys
import time, datetime
import RPi.GPIO as GPIO
import xmlrpclib
import json

GPIO.setwarnings(False)
	
GPIO.setmode(GPIO.BOARD)

userID = 0
#url = 'http://192.168.1.241:8084/tester/workerlogger/api/'#URL
odoo_conn = {
	'url': 'http://192.168.1.166:8069',
	'db': 'Ebay_testing',
	'username': 'admin', #change, put restricted user
	'password': 'jasveznam'
}

def init():
	
	#GREEN
	GPIO.setup(11, GPIO.OUT)
	GPIO.output(11, GPIO.LOW)
	#RED
	GPIO.setup(12, GPIO.OUT)
	GPIO.output(12, GPIO.LOW)
	#YELLOW
	GPIO.setup(15, GPIO.OUT)
	GPIO.output(15, GPIO.LOW)
	#BUZZER
	GPIO.setup(13, GPIO.OUT)
	GPIO.output(13, GPIO.LOW)
	
	
	read_code()

def read_code():
	common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(odoo_conn['url']))
	rem_uid = common.authenticate(odoo_conn['db'], odoo_conn['username'], odoo_conn['password'], {})
	print "Logged in odoo with uid: %s" % rem_uid
	models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(odoo_conn['url']))
	try:
		barcode = input("Read your barcode: ")
		res = models.execute_kw(odoo_conn['db'], rem_uid, odoo_conn['password'], 'emp.time.tracking', 'barcode_flash', [{'barcode': barcode}])
		print res
		_blink_green()
	except Exception, e:
		
		print e
		_blink_red()




def _blink_green():
	GPIO.output(11, True)
	time.sleep(1)
	GPIO.output(11, False)
	return True

def _blink_red():
	GPIO.output(12, True)
	GPIO.output(13, True)
	time.sleep(1)
	GPIO.output(12, False)
	GPIO.output(13, False)	
	return True
	
init()
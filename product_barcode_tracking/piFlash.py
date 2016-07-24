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
	'url': 'http://151.1.221.23:8069',
	'db': 'SEA_srl',
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
	
	
	
	if _check_log_in() == False:
		res = log_in()
		if res:
			userID = res
			read_code()
		

def _check_log_in():
	if userID == 0:
		GPIO.output(15, False)
		return False
		
	else:
		return True

def log_in():
	code = raw_input("Read your code: ")
	if not code:
		return False
		
	try:
		common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(odoo_conn['url']))
		rem_uid = common.authenticate(odoo_conn['db'], odoo_conn['username'], odoo_conn['password'], {})
		print "Logged in odoo with uid: %s" % rem_uid
		models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(odoo_conn['url']))

		exist = models.execute_kw(odoo_conn['db'], rem_uid, odoo_conn['password'], 'hr.employee', 'search', [[['barcode', '=', code]]])
		if exist:
			uid = code
			print "You are now logged in as user " + str(uid) 
			print "***********WELCOME************"
			GPIO.output(15, True)
		else:
			raise ValueError('No user found')
	except Exception, e:
		print e
		print "Error logging in!"
		return log_in()
		

	return uid
	
def log_out():
	userID = 0
	init()
	
def read_code():
	common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(odoo_conn['url']))
	rem_uid = common.authenticate(odoo_conn['db'], odoo_conn['username'], odoo_conn['password'], {})
	print "Logged in odoo with uid: %s" % rem_uid
	models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(odoo_conn['url']))
	try:
		barcode = input("Read barcode: ")
	
		if barcode:
			if barcode == 1234567890123:
				return log_out()
			
			data = {"barcode": str(barcode), "user_id": userID}
			res = models.execute_kw(odoo_conn['db'], rem_uid, odoo_conn['password'], 'product.tracking', 'create', [data])
			if res:
				#Turn on green light
				_blink_green()
				print "OK"
				
			else:
				#Turn on red light and buzzer
				_blink_red()
				print "Error (not ex)"
	
	except Exception, e:
			print e
			#Turn on red light (and buzzer)
			_blink_red()
			print "Error exc"
			
			
	
	return read_code()

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

from openerp import fields, models, api, _
from openerp.osv import osv
import datetime
import time

class emp_time_tracking(models.Model):
	_name = "emp.time.tracking"
	_order = "check_in desc"
	name = fields.Many2one('hr.employee', string="Worker")
	check_in = fields.Datetime(string="Check in")
	check_in_workplace = fields.Datetime(string="Check in workplace")
	check_out = fields.Datetime(string="Check out")
	check_out_workplace = fields.Datetime(string="Checkout of workplace")
	status = fields.Selection([('out', 'OUT of company'), ('in', 'IN company'), ('out_wp', 'OUT of workplace'), ('in_wp', "IN workplace")], string="Status")
	regular_float  = fields.Float(string="Regular time")
	overtime_float = fields.Float(string="Overtime")
	
	total = fields.Float(string="Total")
	
	in_company_total = fields.Float(string="Total in company")
	

	def barcode_flash(self, cr, uid, vals, context=None):
		dt = datetime.datetime.now()
		#Get open log entries
		worker_id = self.pool.get('hr.employee').search(cr, uid, [("barcode", "=", vals['barcode'])], context=None)
		worker = self.pool.get('hr.employee').browse(cr, uid, worker_id, context=None)
		checkpoint_id = vals['checkpoint_id']
		if not worker_id:
			return {'code':500, 'message': "Worker with that barcode is not found"}
		worker_id = worker_id[0]
		log_id = self.search(cr, uid, [("name.barcode", "=", vals['barcode']), ("status", "in", ["in", 'in_wp', 'out_wp'])], context=None)
		if log_id:
			log = self.browse(cr, uid, log_id, context=None)
			log = log[0]
			if log.status == 'in':
				if checkpoint_id == 0:
					#self.pool.get('hr.mistake_log').create(cr, uid, {"message": 
					#	"Worker tried to log at entrance twice", 'worker_id': worker_id, "date":dt, "checkpoint": checkpoint_id}, context=None)
					return {'code':500, 'message': "You cannot log in two times from same location"}
				if checkpoint_id == 1:
					log.check_in_workplace = dt
					log.status = "in_wp"
					worker.presence = 'in_wp'
					#self.pool.get('hr.employee').write(cr, uid, worker_id, {'presence': "in_wp"}, context=None)
					return {'code':201, 'message': "logged in workplace"}
			elif log.status == 'in_wp':
				if checkpoint_id == 1:
					
					print 'test'
					print (dt - datetime.datetime.strptime(log.check_in_workplace, "%Y-%m-%d %H:%M:%S")).seconds > 1200
					timeout =  (dt - datetime.datetime.strptime(log.check_in_workplace, "%Y-%m-%d %H:%M:%S")).seconds
					if timeout < 10:
						return {'code':502, 'message': "you just logged in, stay in company for a while"}
					if timeout < 1200:
						return {'code':501, 'message': "you just logged in, stay in company for a while"}
					log.check_out_workplace = dt
					log.status = 'out_wp'	
					worker.presence = 'out_wp'

					#self.pool.get('hr.employee').write(cr, uid, worker_id, {'presence': "out_wp"}, context=None)
					return {'code':202, 'message': "logged out of workplace"}
				if checkpoint_id == 0:
					
					log.check_out_workplace = dt
					log.check_out = dt
					check_in_date = datetime.datetime.strptime(log.check_in, "%Y-%m-%d %H:%M:%S")
					check_out_date = datetime.datetime.strptime(log.check_out, "%Y-%m-%d %H:%M:%S")
					wp_in = datetime.datetime.strptime(log.check_in_workplace, "%Y-%m-%d %H:%M:%S")
					wp_out = datetime.datetime.strptime(log.check_out_workplace, "%Y-%m-%d %H:%M:%S")

					(log.regular_float, log.overtime_float, log.total, log.in_company_total) = self.calculate_hours(check_out_date, check_in_date, wp_in, wp_out)
				
					
					log.status = 'out'
					worker.presence = 'out'
					worker.last_logout = dt
					#self.pool.get('hr.employee').write(cr, uid, worker_id, {'presence': "out"}, context=None)
					#self.pool.get('hr.mistake_log').create(cr, uid, {"message": 
					#	"Worker skipped logging at workplace, logged out at the gate", 'worker_id': worker_id, "date":dt, "checkpoint": checkpoint_id}, context=None)
					return {'code':203, 'message': "logged out"}
			elif log.status == 'out_wp' and checkpoint_id == 1:
				#self.pool.get('hr.mistake_log').create(cr, uid, {"message": 
				#		"Worker tried to log out of wp twice!", 'worker_id': worker_id, "date":dt, "checkpoint": checkpoint_id}, context=None)
				return {'code':500, 'message': "Wrong checkpoint!"}
			else:
				
				log.check_out = dt
				check_in_date = datetime.datetime.strptime(log.check_in, "%Y-%m-%d %H:%M:%S")
				check_out_date = datetime.datetime.strptime(log.check_out, "%Y-%m-%d %H:%M:%S")
				wp_in = datetime.datetime.strptime(log.check_in_workplace, "%Y-%m-%d %H:%M:%S")
				wp_out = datetime.datetime.strptime(log.check_out_workplace, "%Y-%m-%d %H:%M:%S")

				(log.regular_float, log.overtime_float, log.total, log.in_company_total) = self.calculate_hours(check_out_date, check_in_date, wp_in, wp_out)
				log.status = "out"
				worker.presence = 'out'
				worker.last_logout = dt
				#self.pool.get('hr.employee').write(cr, uid, worker_id, {'presence': "out", 'last_logout': dt}, context=None)
			return {'code':203, 'message': "logged out"} #loged out
		
		#when not logged in (creating new entry for the day)
		if  worker.last_logout and (dt - datetime.datetime.strptime(worker.last_logout, "%Y-%m-%d %H:%M:%S")).seconds < 1200:
			return {'code':505, 'message': "you just logged out, cannot log back in yet!"}
		if checkpoint_id == 0:
			status = 'in'
		elif checkpoint_id == 1:
			status = 'in_wp'
			#Log error
			msg = "Person skipped first check in at the gate, only checked in at workplace"
			#self.pool.get('hr.mistake_log').create(cr, uid, {"message": msg, 'worker_id': worker_id, "date":dt, "checkpoint": checkpoint_id}, context=None)

		nvals = {
			'name': worker_id,
			'check_in': dt,
			'check_in_workplace': dt if status=="in_wp" else None,
			'status': status
		}
		worker.presence = status
		#self.pool.get('hr.employee').write(cr, uid, worker_id, {'presence': status}, context=None)
		self.create(cr, uid, nvals, context=None)
		return {'code':200, 'message': "logged in entrance"} 
	def finish_day(self, cr, uid, ids, context=None):
		log = self.browse(cr, uid, ids, context=None)
		check_in_date = datetime.datetime.strptime(log.check_in, "%Y-%m-%d %H:%M:%S")
		check_out_date = datetime.datetime.strptime(log.check_out, "%Y-%m-%d %H:%M:%S")
		wp_in = datetime.datetime.strptime(log.check_in_workplace, "%Y-%m-%d %H:%M:%S")
		wp_out = datetime.datetime.strptime(log.check_out_workplace, "%Y-%m-%d %H:%M:%S")
		(log.regular_float, log.overtime_float, log.total, log.in_company_total) = self.calculate_hours(check_out_date, check_in_date, wp_in, wp_out)
		log.status = "out"
		self.pool.get('hr.employee').write(cr, uid, log.name.id, {'presence': "out"}, context=None)

	def calculate_hours(self,out_time, in_time, wp_in, wp_out):
		diff_sec = (wp_out - wp_in).seconds
		overtime = 0
		#overtime_format = None
		diff_float = float(diff_sec)
		#sec->hour
		diff_hours_float =diff_float/3600

		if diff_hours_float>8:
			regular = 8
			#regular_format = str(datetime.timedelta(hours=8))

			overtime = diff_hours_float - 8
			#overtime_format = str(datetime.timedelta(seconds=overtime*3600))
		else:
			regular = diff_hours_float
			#regular_format = str(datetime.timedelta(seconds=diff_float))
		total = diff_float/3600
		#total_format = str(datetime.timedelta(seconds=diff_sec))

		diff_sec_in_company = (out_time-in_time).seconds
		diff_hour_in_company = float(diff_sec_in_company)/3600
		#diff_wp_format = str(datetime.timedelta(seconds=diff_sec_wp))

		return regular, overtime, total, diff_hour_in_company#regular_format, overtime_format, total,total_format, diff_hour_wp, diff_wp_format



class hr_mistake_log(models.Model):
	_name = "hr.mistake_log"

	worker_id = fields.Many2one('hr.employee',string="Worker")
	message = fields.Char(string="Message")
	date = fields.Datetime(string="Time")
	checkpoint = fields.Selection([('0', 'Gate'), ('1', 'Workplace')],string="Checkpoint")
from openerp import fields, models, api, _
from openerp.osv import osv
import datetime
import time
import logging

class hr_employee(models.Model):
	_inherit = "hr.employee"

	presence = fields.Selection([("in", 'Inside company, but not at workplace'),
		('in_wp', 'At workplace'), ('out_wp', "Out of workplace but still in company"), ('out', "OUT")], string="Presence status")

	timesheets = fields.One2many('emp.time.tracking', 'name', string="Timesheets")
	absent_id = fields.Integer(string="Absent_id_fk")
	father_name = fields.Char(string="Father name")
	street = fields.Char(string="Street")
	city = fields.Char(string="City")
	personal_phone = fields.Char(string="Personal phone")
	last_logout = fields.Datetime(string="Last apperance")
	exclude_from_tracking = fields.Boolean(string="Exclude from checks")

	def create(self, cr, uid, data, context=None):
		context = dict(context or {})
		if context.get("mail_broadcast"):
			context['mail_create_nolog'] = True

		employee_id = super(hr_employee, self).create(cr, uid, data, context=context)
		empty_len = 11-len(str(employee_id))
		empties = ""
		for i in range(0, empty_len):
			empties += "0"
		bc = "69%s%s" % (empties, employee_id)
		self.write(cr, uid, employee_id, {'barcode': bc}, context=None)

		if context.get("mail_broadcast"):
			self._broadcast_welcome(cr, uid, employee_id, context=context)
		return employee_id



class absent_worker(models.Model):
	_name = "absent.worker"

	date = fields.Datetime(string="Date")
	workers = fields.One2many('hr.employee', 'absent_id', string="Absent workers")

	total_absent = fields.Integer(string="total_absent")

	def get_workers(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)


		workers_contracts1 = self.pool.get('hr.contract').search(cr, uid, [("date_start", "<", datetime.datetime.now()), ("employee_id.active", "=", True)], context=None)
		#_logger.info("***** W1: %s" % workers_contracts1)
		workers_contracts2 = self.pool.get('hr.contract').search(cr, uid, ['|',("date_end", ">", datetime.datetime.now()), ("date_end", "=", False)], context=None)
		#_logger.info("***** W2: %s" % workers_contracts2)
		intsc = set(workers_contracts1).intersection(workers_contracts2)

		workers_contracts = list(intsc)

		tz = 2
		record = self.browse(cr, uid, ids, context=None)[0]
		self.pool.get('hr.employee').write(cr, uid, [x.id for x in record.workers], {'absent_id': None}, context=None)
		c_d = datetime.datetime.strptime(record.date, "%Y-%m-%d %H:%M:%S")
		current = {
					'dow': c_d.weekday(),#datetime.datetime.today().weekday(),

					'hour': float(c_d.minute)/60 + float(c_d.hour) + 2 #EUROPE TIMEZONE

		}
		print "CURRENT: ", current
		absent = 0
		for wc in self.pool.get('hr.contract').browse(cr, uid, workers_contracts, context=None):
			if wc.employee_id.exclude_from_tracking:
				continue
			for schedules in wc.working_hours.attendance_ids:
				dow = schedules.dayofweek
				hf = schedules.hour_from
				ht = schedules.hour_to
				if int(current['dow']) == int(dow) and current['hour'] >= hf and current['hour'] <= ht:
					_logger.info("SHOULD BE HERE: %s" % wc.employee_id.name)
					if wc.employee_id.presence != 'in_wp':
						#present += wc.employee_id.name + "\n"
						self.pool.get('hr.employee').write(cr, uid, wc.employee_id.id, {'absent_id':ids[0]}, context=None)
						absent +=1

		self.write(cr, uid, ids, {'total_absent':absent}, context=None)


		return True

class worker_timesheet_summary(models.Model):
	_name = "emp.tracking.timesheet.summary"

	date = fields.Datetime(string="Date")
	exact_date = fields.Boolean(string="Use exact date")
	workers = fields.One2many('emp.tracking.summary.line', 'tracking_id')


	def get_workers(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)
		self.pool.get('emp.tracking.summary.line').unlink(cr, uid, self.pool.get('emp.tracking.summary.line').search(cr, uid, [],context=None), context=None)
		data = []

		#workers_contracts = self.pool.get('hr.contract').search(cr, uid, [("date_end", ">", datetime.datetime.now())], context=None)
		emp_ids = self.pool.get('hr.employee').search(cr, uid, [], context=None)
		emps = self.pool.get('hr.employee').browse(	cr, uid, emp_ids, context=None)
		record = self.browse(cr, uid,ids, context=None)[0]
		this_month = int((datetime.datetime.strptime(record.date, "%Y-%m-%d %H:%M:%S")).month)
		this_day = int((datetime.datetime.strptime(record.date, "%Y-%m-%d %H:%M:%S")).day)
		exact = record.exact_date


		for emp in emps:
			if emp.exclude_from_tracking:
				continue
			regular = 0.0
			overtime = 0.0
			total = 0.0
			contracts = emp.contract_ids
			if contracts:

				contract = None
				for c in contracts:
					c_start = (datetime.datetime.strptime(c.date_start, "%Y-%m-%d")).month
					c_end = (datetime.datetime.strptime(c.date_end, "%Y-%m-%d")).month if c.date_end else None
					if this_month >= c_start and (this_month <= c_end or not c_end):
						contract = c
						_logger.info("FOUND CONTRACT %s" % contract.name)
						break

			for e in emp.timesheets:
				check_in_month = int((datetime.datetime.strptime(e.check_in, "%Y-%m-%d %H:%M:%S")).month)
				check_in_day = int((datetime.datetime.strptime(e.check_in, "%Y-%m-%d %H:%M:%S")).day)
				check_in_dow = int((datetime.datetime.strptime(e.check_in, "%Y-%m-%d %H:%M:%S")).weekday())

				check_in_workplace = e.check_in_workplace
				if not check_in_workplace:
					continue

				check_out_workplace = e.check_out_workplace
				if not check_out_workplace:
					continue

				check_in_workplace = (datetime.datetime.strptime(check_in_workplace, "%Y-%m-%d %H:%M:%S")).time()
				check_in_workplace = datetime.timedelta(hours=check_in_workplace.hour + 2, minutes=check_in_workplace.minute, seconds=check_in_workplace.second).seconds

				check_out_workplace = (datetime.datetime.strptime(check_out_workplace, "%Y-%m-%d %H:%M:%S")).time()
				check_out_workplace = datetime.timedelta(hours=check_out_workplace.hour + 2, minutes=check_out_workplace.minute, seconds=check_out_workplace.second).seconds

				check_in_workplace = float(check_in_workplace) / float(3600)
				check_out_workplace = float(check_out_workplace) / float(3600)

				if not check_in_month == this_month:
					continue
				if exact and not check_in_day == this_day:
					continue
				if contract:
					for att in contract.working_hours.attendance_ids:
						#print att.dayofweek
						if int(att.dayofweek) == int(check_in_dow):
							_logger.info("FOUND DAY OF WEEK")
							print check_in_dow

							print att.hour_from, check_in_workplace, check_out_workplace



							if not att.hour_from or not att.hour_to:
								break

							df_in = att.hour_from - check_in_workplace
							df_out = att.hour_to - check_out_workplace


							if (df_in< 0 and df_in > -0.15) or (df_in > 0 and df_in < 1):
								check_in_workplace = att.hour_from
								_logger.info("GOING WITH TIME IN: %s (%s)" % (check_in_workplace, df_in))

							if df_out< 0 and df_out > -0.25:
								check_out_workplace = att.hour_to
								_logger.info("GOING WITH TIME OUT: %s (%s)" % (check_out_workplace, df_out))


				this_reg = check_out_workplace - check_in_workplace
				this_ot = 0
				if this_reg > 8:
					this_ot = this_reg - 8
					this_reg = 8


				print this_reg, this_ot
				#this_reg = float(e.regular_float) or 0.0
				#this_ot = float(e.overtime_float) or 0.0
				regular += this_reg
				overtime += this_ot
				total += (this_reg + this_ot) or 0.0
			if True:
				vals = {
					'name': emp.id,
					'id_no': emp.identification_id,
					'regular': regular,
					'overtime': overtime,
					'total': total,
					'tracking_id': ids[0]
				}
				print self.pool.get('emp.tracking.summary.line').create(cr, uid, vals, context=None)
				data.append(vals)
		print data
		return True



class timesheet_summary_line(models.Model):
	_name = "emp.tracking.summary.line"

	name = fields.Many2one('hr.employee', string="Worker")
	id_no = fields.Char(string="Identification number")
	regular = fields.Float(string="Regular")
	overtime = fields.Float(string="Overtime")
	total = fields.Float(string="Total")
	tracking_id = fields.Integer()

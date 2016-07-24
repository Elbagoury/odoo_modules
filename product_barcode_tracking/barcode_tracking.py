from openerp import fields, models, api
import datetime
import logging

class tracking_invoice_line(models.Model):
	_name = "tracking.invoice.line"
	def create(self, cr, uid, vals, context=None):
		_logger = logging.getLogger(__name__)
		_logger.info("*********VALS %s" % vals)
		vals = vals[0]
		invoice_number = vals['invoice_number']
		invoice_id = self.pool.get('account.invoice').search(cr, uid, [("number", '=', invoice_number)], context=None)
		_logger.info("**********INVOICE %s" % invoice_id)
		if not invoice_id:
			_logger.info("****NO INVOICE")
		invoice_id =invoice_id[0]
		invoice = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=None)
		product_code = vals['product_code']
		p_id = self.pool.get('product.product').search(cr, uid, [('name', '=', product_code)], context=None)
		if not p_id:
			_logger.info("*** NO PRODUCT")
		p_id = p_id[0]
		account_id = 1051
		#get earlier invoice lines for this product
		quantity = 1
		for il in invoice.invoice_line:
			_logger.info("*********%s" % il)
			if il.product_id.id == p_id:
				quantity = il.quantity + 1
				il.quantity = quantity
				return True

		vals = {
			'product_id': p_id,
			'quantity': quantity,
			'account_id': account_id,
			'name': vals['description'],
			'price_unit': 1,
			'invoice_id': invoice_id
		}
		_logger.info(vals)
		invoice_line_id = self.pool.get('account.invoice.line').create(cr, uid, vals, context=None)
		return invoice_line_id





class product_tracking(models.Model):
	_name = "product.tracking"

	#name = fields.Char(string="Barcode")
	#product_barcode = fields.Many2one('product.tracking.barcode', string="Product barcode")
	#user_id = fields.Many2one('hr.employee', string="Worker")
	#mo_id = fields.Many2one('mrp.production', string="Manufacturing order")

	
	def create(self, cr, uid, vals, context=None):
		_logger = logging.getLogger(__name__)
		if 'name' not in vals:
			_logger.error("*******NO NAME SENT")
			return False

		rec_id = self.pool.get('product.tracking.barcode').search(cr, uid, [("name", "=", vals['name'])], context=None)
		if not rec_id:
			_logger.error("FATAL - CANT FIND BOUND ROW")
			return
		record = self.pool.get("product.tracking.barcode").browse(cr, uid, rec_id, context)[0]

		wrk_ids = self.pool.get('hr.employee').browse(cr, uid, vals['user_id'], context=None)
		if not wrk_ids:
			print vals['user_id']
			_logger.error("FATAL - NO USER")
			return False
		wrk_id = wrk_ids[0].id
		department = wrk_ids[0].department_id.name
		bc_flash_id = self.pool.get('product.barcode.flash').create(cr, uid, {'worker_id': wrk_id,'department': department}, context=None)

		mo_ids = self.pool.get("mrp.production").search(cr, uid, [("state", "=", "in_production")], context=None)
		if not mo_ids:
			_logger.error("Could not find any MO")
			return False
		mo_id = False
		for mo in self.pool.get('mrp.production').browse(cr, uid, mo_ids, context=None):
			for bom_line in mo.bom_id.bom_line_ids:
				
				if bom_line.product_id.id == record.product_id.id:
					mo_id = mo.id
					break
		if not mo_id:
			_logger.error("Could not bind to any MO: product %s - FATAL" % pro.name)
			return False
		
		data = {'state': "in_production", 'mo_id': mo_id, 'workers': [[4,bc_flash_id]]}
		print data
		record.write(data)
		return True
		
class select_toner(models.Model):
	_name = "tracking.toner.select"

	def create(self, cr, uid, vals, context=None):
		_logger = logging.getLogger(__name__)
		worker_id = vals["worker"]
		toner_id = vals["toner_code"]		
		barcode = vals["barcode"]
		pro_ids = self.pool.get('product.product').search(cr, uid, [('name', '=',toner_id)], context=None)
		if pro_ids:
			pid = pro_ids[0]
			
		else:
			_logger.error("CANT FIND PRODUCTS WITH THAT NAME")
			return False
		worker = self.pool.get('hr.employee').browse(cr, uid, worker_id, context=None)
		if not worker:
			_logger.error("CANT FIND EMPLOYEE")
			return False
		flash ={
			'worker_id': worker.id,
			'department': worker.department_id.name
		}
		flash_id = self.pool.get('product.barcode.flash').create(cr, uid, flash, context=None)
		vals = {
			'product_id': pid,
			'name': barcode,
			'workers': [[4, flash_id]]
		}
		bc_id = self.pool.get('product.tracking.barcode').create(cr, uid, vals, context=None)
		return bc_id

class product_barcodes(models.Model):
	_name = "product.tracking.barcode"

	product_code = fields.Char(string="tech_product_name")
	product_id = fields.Many2one('product.product', string="Product")
	name = fields.Char(string="Product barcode", required=True)

	state = fields.Selection([('not_yet_in_production', 'Not yet in production'), ('in_production', 'In Production'), ('done', 'Done')], string="state", default="not_yet_in_production")
	mo_id = fields.Many2one('mrp.production', string="Manufacturing order")
	workers = fields.One2many('product.barcode.flash', 'tracking_id')

	
	def create(self, cr, uid,vals, context=None):
		_logger = logging.getLogger(__name__)
		if 'product_code' in vals:
			pro_ids = self.pool.get('product.product').search(cr, uid, [('name', '=', vals['product_code'])], context=None)
			if pro_ids:
				pid = pro_ids[0]
				vals['product_id'] = pid
			else:
				_logger.error("CANT FIND PRODUCTS WITH THAT NAME")
				return False
		return super(product_barcodes, self).create(cr, uid,vals, context=context)

class product_tracking_flash(models.Model):
	_name = "product.barcode.flash"
	worker_id = fields.Many2one('hr.employee', string="Worker")
	department = fields.Char(string="Department")
	timestamp = fields.Datetime(default=datetime.datetime.now(), string="TimeOfFlash")
	tracking_id = fields.Integer(string="Tracking ID")
	
class mrp(models.Model):
	_inherit = "mrp.product.produce"

	def do_produce(self, cr, uid, ids, context=None):
		production_id = context.get('active_id', False)
		assert production_id, "Production Id should be specified in context as a Active ID."
		data = self.browse(cr, uid, ids[0], context=context)
		self.pool.get('mrp.production').action_produce(cr, uid, production_id,
                            data.product_qty, data.mode, data, context=context)
		tracking_ids = self.pool.get('product.tracking.barcode').search(cr, uid, [("mo_id.id", "=", production_id)], context=None)
		if tracking_ids:
			self.pool.get('product.tracking.barcode').write(cr, uid, tracking_ids, {'state': 'done'}, context=None)
		return {}

from openerp import models, fields, _
from openerp.osv import osv
import xmlrpclib
import logging

class product_compare(models.Model):
	_name = "product.compare"

	name = fields.Char()
	url = fields.Char()
	db = fields.Char()
	user = fields.Char()
	pwd = fields.Char()
	sync_images = fields.Boolean()
	add_all = fields.Boolean(string="Update all products regardless of the difference")
	field_to_check = fields.Many2many('ir.model.fields',  domain=[('model', '=', 'product.template'),('name', '!=', 'name'), ('name', '!=', 'image'),('ttype', 'not in', ['one2many',  'reference', 'function'])], required=True)

	lines = fields.One2many('product.compare.line', 'compare_id')
	categories = fields.One2many('product.compare.category', 'compare_id')
	def refreshFromProduct(self, cr, uid, ids, context=None, product_id = None):
		_logger = logging.getLogger(__name__)
		line_ids = self.pool.get('product.compare').search(cr, uid, [], context=None)
		_logger.info("---------- LINE_IDS: %s" % line_ids)
		for line in line_ids:
			_refresh_all(self, cr, uid, [line], context=context, product_id = product_id)


	def syncFromProduct(self, cr, uid, ids, context=None, product_id=None):
		_logger = logging.getLogger(__name__)

		line_ids = self.pool.get('product.compare').search(cr, uid, [], context=None)
		_logger.info("---------- LINE_IDS SYNC: %s" % line_ids)

		for line in line_ids:
			_sync(self, cr, uid, [line], context=None, product_id=product_id)

	def updatePricesFromProduct(self, cr, uid, ids, context=None, product_id=None):
		line_ids = self.pool.get('product.compare').search(cr, uid, [], context=None)
		for line in line_ids:
			self.pool.get('product.compare').updatePrices(cr, uid, [line], context=None, product_id = ids)

	def getList(self, cr, uid, ids, context=None):
		_refresh_all(self, cr, uid, ids, context=context)
		return True
	def sync(self, cr, uid, ids, context=None):
		_sync(self, cr, uid, ids, context=context)
		return True
	def refreshCats(self, cr, uid, ids, context=None):
		_refresh_cats(self, cr, uid, ids, context=None)
		return True
	def updatePrices(self, cr, uid, ids, context=None, product_id=None):
		_logger = logging.getLogger(__name__)
		_logger.info("PRODUCT PRICE UPDATE ID: %s" % product_id)
		product_ids = product_id or self.pool.get('product.template').search(cr, uid, [('active', '=', True)], context=None)
		products = self.pool.get('product.template').browse(cr, uid, product_ids, context=None)

		record = self.browse(cr, uid, ids, context)[0]

		url = record.url
		db = record.db
		username = record.user
		password = record.pwd
		common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
		#print common.version

		rem_uid =  common.authenticate(db, username, password, {})
		_logger.info("_______USER ID ON REMOTE ODOO FOR USER admin is: %s" % rem_uid)
		models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(url))
		cnt = 0
		for p in products:
			if not p.default_code:
				continue
			rem_p_id = models.execute_kw(db, uid, password,
				'product.template', 'search', [[['default_code', '=', p.default_code]]])
			if rem_p_id:
				models.execute_kw(db, uid, password,
					'product.template', 'write', [rem_p_id, {'list_price': p.list_price, 'net_price': p.net_price}])
				cnt += 1
				_logger.info("----UPDATED %s (%s)" % (p.default_code, cnt))


class product_compare_line(models.Model):
	_name = "product.compare.line"

	product_id = fields.Many2one('product.template',string="Product ID")
	description = fields.Char(string="Description")
	default_code = fields.Char(string="Internal reference")
	code_for_foreign = fields.Char(string="Product code on remote odoo")
	category_foreign = fields.Char(string="Category foreign")
	info_diff = fields.Boolean(string="Only info diff")
	compare_id = fields.Integer()


def _refresh_all(self, cr, uid, ids, context=None, product_id = None):
		_logger = logging.getLogger(__name__)
		record = self.browse(cr, uid, ids, context)[0]
		for item in record.lines:
			if product_id:
				if item.product_id.id in product_id:
					item.unlink()
			else:
				item.unlink()

		addAll = record.add_all
		url = record.url
		db = record.db
		username = record.user
		password = record.pwd
		common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
		#print common.version

		rem_uid =  common.authenticate(db, username, password, {})
		print "USER ID ON REMOTE ODOO FOR USER admin is: %s" % rem_uid
		models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(url))
		if product_id:
			products = self.pool.get('product.template').browse(cr, uid, product_id, context=None)
			pro_ids = []
			for p in products:
				categ_ids = [x.id for x in p.categ_id.foreign_binding]
				if record.id in categ_ids:
					pro_ids.append(p.id)
		else:
			pro_ids = self.pool.get('product.template').search(cr, uid, [("categ_id.foreign_binding", "ilike", record.id), ('active', '=', True)])

		_logger.info("***********PRODUCTS THAT SHOULD BE ON THIS COMPANY: %s" % len(pro_ids))
		#return True
		#DEBUGGING
		#products = self.pool.get('product.template').browse(cr, uid, pro_ids, context=None)
		#print "PRODUCTS ARE: %s" % [x.name for x in products]
		if not record.field_to_check:
			print "NO FIELDS TO CHECK"
			return True

		to_check = [x for x in record.field_to_check]
		to_retrieve = [x.name for x in record.field_to_check]
		to_retrieve.append('name')
		to_retrieve.append('categ_id')

		#ENDING
		#return True

		if record.sync_images:
			to_retrieve.append('image')

		for p in self.pool.get('product.template').browse(cr, uid, pro_ids, context=None):
			if not p.default_code:
				_logger.info("skipping %s" % p.name)
				continue
			_logger.info("going with %s" % p.name)
			f_ids = models.execute_kw(db, uid, password, 'product.template', 'search', [[['default_code', '=', p.default_code]]])

			if f_ids:
				#BREAKER#BREAKER#BREAKER#BREAKER
				#continue
				#BREAKER#BREAKER#BREAKER#BREAKER
				f_pro = models.execute_kw(db, uid, password, 'product.template', 'read', [f_ids], {'fields': to_retrieve})[0]
				_logger.info("exists %s" % f_pro)
				hasDifference = False
				for field in to_check:

					if p[field.name]:
						#check master type
						if field.ttype in ['many2many', 'many2one']:
							value = p[field.name].id
							slave = False
							if f_pro[field.name]:
								slave = f_pro[field.name][0]
						else:
							value = p[field.name]
							slave = f_pro[field.name]


						if value != slave:
							hasDifference = True
							_logger.info("%s ********* DIFFERENT OR NO %s" % (p.default_code, field.name))
					elif f_pro[field.name]:
						hasDifference = True


				if hasDifference or addAll:
					_logger.info("******** in setting %s" % p.default_code)

					vals = {
						'product_id': p.id,
						'description': p.description,
						'default_code': p.default_code,
						'code_for_foreign': f_pro['name'],
						'info_diff': True,
						'compare_id': record.id,
						'category_foreign': f_pro['categ_id'][1]
					}
					self.pool.get('product.compare.line').create(cr, uid, vals, context=context)
				_logger.info("Exists but no diff")
			else:
				_logger.info("dont exist %s" % p.name)
				vals = {
					'product_id': p.id,
					'description': p.description,
					'default_code': p.default_code,
					'compare_id': record.id
				}
				self.pool.get("product.compare.line").create(cr, uid, vals, context=context)



		return True

def _sync(self, cr, uid, ids, context=None, product_id = None):
	_logger = logging.getLogger(__name__)
	record = self.browse(cr, uid, ids, context)[0]

	url = record.url
	db = record.db
	username = record.user
	password = record.pwd
	common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
	#print common.version


	rem_uid =  common.authenticate(db, username, password, {})
	_logger.info("_______USER ID ON REMOTE ODOO FOR USER admin is: %s" % rem_uid)
	models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(url))

	to_check = [x for x in record.field_to_check]
	cat_map_obj = self.pool.get('product.compare.category')

	cat_map = cat_map_obj.browse(cr, uid, cat_map_obj.search(cr, uid, [], context=None), context=None)

	if len(record.lines) == 0:
		return True

	counter = 0
	r_lines = []
	if product_id:
		for p in record.lines:
			if p.product_id.id in product_id:
				r_lines.append(p)

	else:
		r_lines = record.lines
	for p in r_lines:

		#if counter > 200:
			#break
		try:
			if not p.product_id.default_code:
				_logger.info("NO INTERNAL REFERENCE")
				continue

			if p.code_for_foreign:
				f_id = models.execute_kw(db, uid, password, 'product.template', 'search', [[['default_code', '=', p.product_id.default_code]]])
				_logger.info("****************EXISTS: %s" % f_id)

				_logger.info("********************in create %s" % p.product_id.name)
				vals = {}
				vals['name'] = p.code_for_foreign

				vals['categ_id'] = p.product_id.categ_id.id
				for cm in cat_map:

					if cm.local_cat.id == p.product_id.categ_id.id and cm.compare_id.id == record.id:
						_logger.info("going with mapped category")
						vals['categ_id'] = cm.remote_cat

				_logger.info(vals)
				if record.sync_images and p.product_id.image:
					vals['image'] = p.product_id.image
				for f in to_check:

					if f.ttype == 'many2one':
						vals[f.name] = p.product_id[f.name].id
					elif f.ttype == 'many2many':
						vals[f.name] = [[4, p.product_id[f.name].id]]
					else:
						vals[f.name] = p.product_id[f.name]
					print vals

				if not f_id:
					vals['default_code'] = p.product_id.default_code
					models.execute_kw(db, uid, password, 'product.template', 'create', [vals])
				else:
					f_id = f_id[0]
					vals.pop('categ_id')
					updated = models.execute_kw(db, uid, password, 'product.template', 'write', [[f_id], vals])
					_logger.info("************** %s" % updated)

				p.unlink()
				counter +=1
		except:
			#raise osv.except_osv(_('Sync error'), _('There`s been an error trying to sync item %s. Check if category %s exists on other company and if its entered in category mapping table' % (p.product_id.name, p.product_id.categ_id.name)))

			continue


	return True #_refresh_all(self, cr, uid, ids, context=None)

#EXPERIMENTAL
def _refresh_cats(self, cr, uid, ids, context=None):
		record = self.browse(cr, uid, ids, context)[0]
		for category in record.categories:
			category.unlink()
		url = record.url
		db = record.db
		username = record.user
		password = record.pwd
		common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
		#print common.version

		rem_uid =  common.authenticate(db, username, password, {})
		print "USER ID ON REMOTE ODOO FOR USER admin is: %s" % rem_uid
		models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(url))

		cat_ids = self.pool.get('product.category').search(cr, uid, [], context=None)
		print "LENGHT: %s" % cat_ids
		local_cats = [{'name':x.name, 'id': x.id, 'parent_id': x.parent_id.id} for x in self.pool.get('product.category').browse(cr, uid, cat_ids, context=None)]

		for c in local_cats:
			f_id = models.execute_kw(db, uid, password, 'product.category', 'search', [[['name', '=', c['name']]]])
			if not f_id:

				self.pool.get('product.compare.category').create(cr, uid, {"local_cat": c['id'], "compare_id": record.id}, context=None)
			else:

				f_cat = models.execute_kw(db, uid, password, 'product.category', 'read', [f_id], {'fields': ['name', 'parent_id']})[0]
				parent = False
				if not f_cat['parent_id']:
					parent = True
				elif f_cat['parent_id'] != c['parent_id']:
					parent = True
				if f_id[0] != c['id']:#or parent:
					self.pool.get('product.compare.category').create(cr, uid, {"local_cat": c['id'], "compare_id": record.id, "wrong_id": True, "remote_cat": f_id[0]}, context=None)

		return True
#END EXPERIMENTAL
class product_category(models.Model):
	_inherit = "product.category"

	foreign_binding = fields.Many2many('product.compare')

class product_compare_category(models.Model):
	_name = "product.compare.category"

	local_cat = fields.Many2one('product.category', string="Local category")
	remote_cat = fields.Integer(string="Remote category ID")
	wrong_id = fields.Boolean(string="Wrong id")
	compare_id = fields.Many2one('product.compare', string="Compare ID")

class product_template(models.Model):
	_inherit = "product.template"

	compare_lines = fields.One2many('product.compare.line', 'product_id', string="Compare lines")

	def refresh_lines(self, cr, uid, ids, context=None):
		self.pool.get('product.compare').refreshFromProduct(cr, uid, ids, context=None, product_id=ids)
	def sync_lines(self, cr, uid, ids, context=None):
		self.pool.get('product.compare').syncFromProduct(cr, uid, ids, context=None, product_id=ids)
	def update_prices(self, cr, uid, ids, context=None):
		self.pool.get('product.compare').updatePricesFromProduct(cr, uid, ids, context=None, product_id=ids)

class category_mapping(models.Model):
	_name = "product.compare.category.mapping"

	local = fields.Many2one('product.category', string="Local category")
	remote = fields.Integer(string="Remote category")

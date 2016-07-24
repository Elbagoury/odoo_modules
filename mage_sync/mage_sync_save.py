from openerp import models, fields, api, _
from openerp.osv import osv
import urllib2, urllib
from openerp.osv import osv
import datetime
from magento_api import MagentoAPI
import base64
import logging
import csv
import sys
import os
import base64
import traceback
import codecs
from openerp import tools
import time

class Magento_sync(models.Model):
	_name = 'magento_sync'

	name = fields.Char()
	categories_exported = fields.Datetime()
	products_exported = fields.Datetime()
	products_exported_all = fields.Datetime()
	customers_exported = fields.Datetime()
	stock_exported = fields.Datetime()
	pricelists_exported = fields.Datetime()
	so_imported = fields.Datetime()

	mage_location = fields.Char(string="Mage location")
	mage_port = fields.Integer(default=80, string="Mage port")
	mage_user = fields.Char(string="Mage user")
	mage_pwd = fields.Char(string="Mage PWD")
	root_category = fields.Integer(string="Mage root cat")

	product_cron = fields.Many2one('ir.cron')
	customer_cron = fields.Many2one('ir.cron')
	orders_cron = fields.Many2one('ir.cron')
	categories_cron = fields.Many2one('ir.cron')


	def cron_export_categories(self, cr, uid, ids=1, context=None):
		try:
			self.export_categories(self, cr, uid, ids, context=None)
			self.pool.get('cron.log').create(cr, uid, {'name':'Magento Category Export', 'description': "Cron Succeded", 'status':0, 'date': datetime.datetime.now()}, context=None)

		except:
			self.pool.get('cron.log').create(cr, uid, {'name':'Magento Category Export', 'description': "Cron failed", 'status':1, 'date': datetime.datetime.now()}, context=None)

		

	def export_categories(self, cr, uid, ids, context=None):
		for record in self.browse(cr, uid, ids, context=context):
			r = record

		cs = {
				'location': r.mage_location,
				'port': r.mage_port,
				'user': r.mage_user,
				'pwd': r.mage_pwd
		}
		
		_export_categories(self, cr, uid, cs)
		
		
		r.categories_exported = datetime.datetime.utcnow()
		return True

	def cron_export_products(self, cr, uid, ids=1, context=None):
		try:
			self.export_products(self, cr, uid, ids, context=None)
			self.pool.get('cron.log').create(cr, uid, {'name':'Magento Product Export', 'description': "Cron Succeded", 'status':0, 'date': datetime.datetime.now()}, context=None)
		except:
			self.pool.get('cron.log').create(cr, uid, {'name':'Magento Product Export', 'description': "Cron failed", 'status':1, 'date': datetime.datetime.now()}, context=None)


	def export_products(self, cr, uid, ids, context = None):
			for record in self.browse(cr, uid, ids, context=context):
				r = record

			cs = {
				'location': r.mage_location,
				'port': r.mage_port,
				'user': r.mage_user,
				'pwd': r.mage_pwd
			}

			_export_products(self, cr, uid, False, cs)

			
			r.products_exported = datetime.datetime.utcnow()
			return True
					

	def export_products_all(self, cr, uid, ids=1, context = None):
			for record in self.browse(cr, uid, ids, context=context):
				r = record

			cs = {
				'location': r.mage_location,
				'port': r.mage_port,
				'user': r.mage_user,
				'pwd': r.mage_pwd
			}
			_export_products(self, cr, uid, True, cs)

			
			r.products_exported = datetime.datetime.utcnow()
			r.products_exported_all = datetime.datetime.utcnow()
			
			return True

	#TEST TEST
	
			
	def cron_export_customers(self, cr, uid, ids=1, context=None):	
		return export_customers(self, cr, uid, ids, context=None)
	def export_customers(self, cr, uid, ids, context = None, client_id=None):
			for record in self.pool.get('magento_sync').browse(cr, uid, ids, context=context):
				r = record
			_logger = logging.getLogger(__name__)
			magento = MagentoAPI(r.mage_location, r.mage_port, r.mage_user, r.mage_pwd)
			
			client_ids = self.pool.get('res.partner').search(cr, uid, [("sync_to_mage", "=", True), ("email", "!=", False), ("customer", "=", True),("mage_customer_pass", "!=", False), ("last_name", "!=", False),("city", "!=", False), ("zip", "!=", False),("street", "!=", False), ("phone", "!=", False)], context=None)
			if client_id:
				clients = self.pool.get('res.partner').browse(cr, uid, client_id, context=None)
			else:
				clients = self.pool.get('res.partner').browse(cr, uid, client_ids, context=None)
			_logger.warning("**********CUSTOMER COUNT: %s" % len(clients))
			for c in clients:
				_logger.info("*****************CUSTOMER: %s - %s" % (c.name, c.magento_id))
				c.email = c.email.lstrip()
				client = {
					'email': c.email,
					'firstname': c.name,
					'lastname': c.last_name,
					'password': c.mage_customer_pass,
					'website_id': 1,
					'store_id': 1,
					'group_id':1
				}

				address = [[c, {
						'city': c.city,
						'company': c.name,
						'country_id': c.country_id.code,
						'firstname': c.name,
						'lastname': c.last_name,
						'postcode': c.zip,
						'street': c.street,
						'telephone': c.phone,
						'is_default_billing': 1,
						'is_default_shipping': 1
					}]]
				shipp_ids = self.pool.get('res.partner').search(cr, uid, [("parent_id", "=", c.id), ("type", "=", "delivery")], context=None)
				if shipp_ids:
					shipp = self.pool.get('res.partner').browse(cr, uid, shipp_ids, context=None)
					for s in shipp:
						last_nm = c.last_name
						if s.last_name:
							last_nm = s.last_name
						a = [s, {
							'city': s.city,
							'company': c.name,
							'country_id': s.country_id.code,
							'firstname': s.name,
							'lastname': last_nm,
							'postcode': s.zip,
							'street': s.street,
							'telephone': s.phone,
							'is_default_shipping': 1,
							'is_default_billing': 0
							}]
						address.append(a)
				
				if not c.magento_id:
					print client
					c.magento_id = magento.customer.create(client)
					print c.magento_id
					print address
					for ad in address:
						ad[0].magento_address_id = magento.customer_address.create(c.magento_id, ad[1])

					print c.magento_address_id
				else:
					is_updated = magento.customer.update(c.magento_id, client)
					print is_updated
					if is_updated and c.magento_address_id:
						for a in address:
							if a[0].magento_address_id:
								print "updating address"
								magento.customer_address.update(a[0].magento_address_id, a[1])
							else:
								print "creating address"
								a[0].magento_address_id = magento.customer_address.create(c.magento_id, a[1])
						
						for ma in magento.customer_address.list(c.magento_id):
							print "in delete address"
							print ma['customer_address_id']
							found = False
							for a in address:
								if int(ma['customer_address_id']) == a[0].magento_address_id:
									print "Found"
									print a[0].magento_address_id
									found = True
									break
							if not found:
								magento.customer_address.delete(ma['customer_address_id'])

						
								

				address = None


			
			r.customers_exported = datetime.datetime.utcnow()
			return True
			


	def export_pricelists(self, cr, uid, ids, context = None):
				try:
						for record in self.browse(cr, uid, ids, context=context):
								url = record.mage_location + "/odoo-mage/prices.php"
								mydata = [('cs', self.get_connection_string(record))]

						mydata = urllib.urlencode(mydata)
						path = url
						req = urllib2.Request(path, mydata)
						req.add_header("Content-type", "application/x-www-form-urlencoded")
						urllib2.urlopen(req)

						for record in self.browse(cr, uid, ids, context=context):
								record.pricelists_exported = datetime.datetime.utcnow()
						return True
				except ValueError:
						print "Error!"
						return False

	def reindex(self, cr, uid, ids, context=None):
		for record in self.browse(cr, uid, ids, context=context):
				r = record

		cs = {
			'location': r.mage_location,
			'port': r.mage_port,
			'user': r.mage_user,
			'pwd': r.mage_pwd
		}
		print cs
		_translate_categories(self, cr, uid, cs)

		return True

	def delete_all(self, cr, uid, ids, context=None):
		for record in self.browse(cr, uid, ids, context=context):
				r = record

		cs = {
				'location': r.mage_location,
				'port': r.mage_port,
				'user': r.mage_user,
				'pwd': r.mage_pwd
		}

		magento = MagentoAPI(cs['location'], cs['port'], cs['user'], cs['pwd'])
		products = magento.catalog_product.list()
		for p in products:
			magento.catalog_product.delete(p['product_id'])

		prod_ids = self.pool.get('product.template').search(cr, uid, [("magento_id", ">", 0)], context=None)
		for po in self.pool.get('product.template').browse(cr, uid, prod_ids, context=context):
			po.magento_id = 0

		cat_ids = self.pool.get('product.category').search(cr, uid, [("magento_id", ">", 0)], context=None)
		for co in self.pool.get('product.category').browse(cr, uid, cat_ids, context=context):
			co.magento_id = 0

		categories = magento.catalog_category.tree()
		cats = _sort_categories(categories)

		for c in cats:
			if c['id'] > 2:
				#magento.catalog_category.delete(c['id'])
				print "a"
		

		return True
	
	def XXcreate_product_cron(self, cr, uid, ids, context=None):
		for record in self.pool.get('magento_sync').browse(cr, uid, 1, context=context):
			r = record

		cs = {
			'location': r.mage_location,
			'port': r.mage_port,
			'user': r.mage_user,
			'pwd': r.mage_pwd
		}
		increment_id = '100000002'
		itemQty = {
			'order_item_id':'65',
			'qty': '1'
		}
		itemQtys = []
		itemQtys.append(itemQty)
		print itemQtys 
		print increment_id
		return _export_invoice(increment_id, itemQtys, cs)
	def create_product_cron(self, cr, uid, ids, context=None):
		for record in self.browse(cr, uid, ids, context):
			r = record
		r.product_cron = _create_cron(self, cr, uid, "Magento Product Export", "mage_pro_export", "cron_export_products", 1, "days")
		return True
	def create_customer_cron(self, cr, uid, ids, context=None):
		for record in self.browse(cr, uid, ids, context):
			r = record
		r.customer_cron = _create_cron(self, cr, uid, "Magento Customer Export", "mage_cust_export", "cron_export_customers", 60, "minutes")
		return True
	def create_orders_cron(self, cr, uid, ids, context=None):
		for record in self.browse(cr, uid, ids, context):
			r = record
		r.orders_cron = _create_cron(self, cr, uid, "Magento Orders Import", "mage_order_import", "cron_import_orders", 10, "minutes")
	
	def create_categories_cron(self, cr, uid, ids, context=None):
		for record in self.browse(cr, uid, ids, context):
			r = record
		r.categories_cron = _create_cron(self, cr, uid, "Magento Category export", "mage_category_export", "cron_export_categories", 2, "days")

#**************************AHHH, IMPOSTER************************************
	def SDdelete_all_products(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)
		product_ids = self.pool.get('product.template').search(cr, uid, [("name", "ilike", "\"")], context=None)
		_logger.warning("************FOUND: %s" % len(product_ids))
		self.pool.get('product.template').write(cr, uid, product_ids, {'active': False} ,context=None)
		variant_ids = self.pool.get('product.product').search(cr, uid, [("name", "ilike", "\"")], context=None)
		self.pool.get('product.product').write(cr, uid, variant_ids, {'active': False}, context=None)
		return True
	def delete_all_products(self, cr, uid, ids, context=None):
		if False:
			client_ids = self.pool.get('res.partner').search(cr, uid, [], context=None)
			self.pool.get('res.partner').write(cr, uid, client_ids, {'active': False}, context=None)
		client_ids = self.pool.get('res.partner').search(cr, uid, [], context=None)
		self.pool.get('res.partner').write(cr, uid, client_ids, {'last_name': '-'}, context=None)
		return True
	def ALLTOGETHERdelete_all_products(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)
		_logger.info("**********MASTER TRUNCATE SEQUENCE**********")
		so_ids = self.pool.get('sale.order').search(cr, uid, [], context=None)
		_logger.info("************SALE ORDERS: %s" % len(so_ids))
		#pc_ids = self.pool.get('crm.phonecall').search(cr, uid, [], context=None)
		#_logger.info("************PHONECALLS: %s" % len(pc_ids))
		inv_ids = self.pool.get('account.invoice').search(cr, uid, [], context=None)
		_logger.info("************INVOICES: %s" % len(inv_ids))
		vou_ids = self.pool.get('account.voucher').search(cr, uid, [], context=None)
		_logger.info("************VOUCHERS: %s" % len(vou_ids))
		bnk_ids = self.pool.get('account.bank.statement').search(cr, uid, [], context=None)
		_logger.info("************BANK STATEMENTS: %s" % len(bnk_ids))
		mv_ids = self.pool.get('account.move').search(cr, uid, [], context=None)
		_logger.info("************MOVES: %s" % len(mv_ids))
		po_ids = self.pool.get('purchase.order').search(cr, uid, [], context=None)
		_logger.info("************PO: %s" % len(po_ids))
		#req_ids = self.pool.get('purchase.requisition').search(cr, uid, [], context=None)
		#_logger.info("************REQUISITIONS: %s" % len(req_ids))
		stmv_ids = self.pool.get('stock.move').search(cr, uid, [], context=None)
		_logger.info("************STOCK MOVE: %s" % len(stmv_ids))
		sinv_ids = self.pool.get('stock.inventory').search(cr, uid, [], context=None)
		_logger.info("************INVENTORY: %s" % len(sinv_ids))
		stq_ids = self.pool.get('stock.quant').search(cr, uid, [], context=None)
		_logger.info("************QUANTS: %s" % len(stq_ids))
		prqord_ids = self.pool.get('procurement.order').search(cr, uid, [], context=None)
		_logger.info("************PROCUREMENT ORDERS: %s" % len(prqord_ids))
		wh_ids = self.pool.get('stock.warehouse').search(cr, uid, [], context=None)
		_logger.info("************WAREHOUSES: %s" % len(wh_ids))
		mo_ids = self.pool.get('mrp.production').search(cr, uid, [], context=None)
		_logger.info("************MOs: %s" % len(mo_ids))
		bom_ids = self.pool.get('mrp.bom').search(cr, uid, [], context=None)
		_logger.info("************BOM: %s" % len(bom_ids))

		#self.pool.get('stock.move').action_cancel(cr, uid, mv_ids, context=None)
		#j_ids = self.pool.get('account.journal').search(cr, uid, [], context=None)
		#self.pool.get('account.journal').write(cr, uid, j_ids, {'update_posted': True}, context=None)
		#self.pool.get('account.move').button_cancel(cr, uid, mv_ids, context=None)
		#self.pool.get('account.invoice').action_cancel(cr, uid, inv_ids, context=None)

		#self.pool.get('sale.order').action_cancel(cr, uid, so_ids, context=None)
		#self.pool.get('crm.phonecall').write(cr, uid, pc_ids, {'active': False}, context=None)
		
		#self.pool.get('account.voucher').write(cr, uid, vou_ids, {'active': False}, context=None)
		#self.pool.get('account.bank.statement').write(cr, uid, bnk_ids,{'active': False}, context=None)
		#self.pool.get('account.move').write(cr, uid, mv_ids,{'active': False}, context=None)
		#self.pool.get('purchase.order').write(cr, uid, po_ids,{'active': False}, context=None)
		#self.pool.get('purchase.requisition').write(cr, uid, req_ids,{'active': False}, context=None)
		
		#self.pool.get('stock.inventory').write(cr, uid, sinv_ids,{'active': False}, context=None)
		#self.pool.get('stock.quant').unlink(cr, uid, stq_ids,{'active': False}, context=None)
		#self.pool.get('stock.warehouse').write(cr, uid, wh_ids,{'active': False}, context=None)
		self.pool.get('mrp.production').write(cr, uid, mo_ids,{'state': 'cancel'}, context=None)
		self.pool.get('stock.move').write(cr, uid, stmv_ids,{'state': 'cancel'}, context=None)
		self.pool.get('procurement.order').write(cr, uid, prqord_ids,{'state': 'cancel'}, context=None)
		self.pool.get('sale.order').write(cr, uid, so_ids,{'state': 'cancel'}, context=None)
		self.pool.get('account.invoice').write(cr, uid, inv_ids,{'state': 'cancel'}, context=None)
		
		#self.pool.get('mrp.production').write(cr, uid, mo_ids,{'active': False}, context=None)
		#self.pool.get('mrp.bom').write(cr, uid, bom_ids,{'active': False}, context=None)

		return True

	def XXdelete_all_products(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)
		var_ids = self.pool.get('product.product').search(cr, uid, [("default_code", "ilike", "Administrator")], context=context)
		_logger.warning("*****FOUND %s VARIANTS" % len(var_ids))
		self.pool.get('product.product').unlink(cr, uid, var_ids, context=context)

		return True

	def XXexport_products_to_csv(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)
		categ_ids = self.pool.get('product.category').search(cr, uid, [], context=None)
		_logger.warning("********* %s" % len(categ_ids))
		categs = self.pool.get('product.category').browse(cr, uid, categ_ids, context=None)
		for c in categs:
			_logger.warning("*********** %s" % c.name)
			c.no_create_variants = False
		
		if False:
			with open('/opt/odoo/ft_cats.csv', 'wb') as csvfile:
				writer = csv.writer(csvfile, delimiter=',',quotechar='|', quoting=csv.QUOTE_MINIMAL)
				
				for p in categs:
					try:
						writer.writerow([p.id] + [p.name])
					except:
						
						continue

		return True

	def ZXCexport_products_to_csv(self, cr, uid, ids, context=None):
		product_ids = self.pool.get('product.template').search(cr, uid, [("active", "=", True)], context=None)
		products = self.pool.get('product.template').browse(cr, uid, product_ids, context=None)

		

		with open('/opt/odoo/ft-for-oem.csv', 'wb') as csvfile:
			writer = csv.writer(csvfile, delimiter=',',quotechar='|', quoting=csv.QUOTE_MINIMAL)
			
			for p in products:
				try:
					writer.writerow([p.default_code] + [p.oem_code] + [p.description])
				except:
					
					continue

		return True

	def export_products_to_csv(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)
		self.pool.get('ir.model.data').get_object_reference(cr, uid, 'res.partner', '193040')[1] 
		_logger.warning("***************** ID: %s" % record_id) 

	
	def VARimport_products_from_csv(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)
		with open('/home/gigra/gigra_variants.csv') as main:
			rdr = csv.reader(main, delimiter=",", quotechar="|")
			product_ids = self.pool.get('product.template').search(cr, uid, [], context=None)
			products = self.pool.get('product.template').browse(cr, uid, product_ids, context=None)
			counter = 0
			for row in rdr:
				if counter > 2:
					return True
				for p in products:
					if row[0] == p.name:
						counter +=1
						pro_vals = {
							'default_code': row[1],
							'product_tmpl_id': p.id
						}
						
						is_created = self.pool.get('product.product').create(cr, uid, pro_vals, context=None)
						_logger.warning("************** %s" % pro_vals)
						_logger.warning("************** THIS IS NUMBER: %s" % counter)
		return True
	def PAYMENTTERMimport_products_from_csv(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)
		terms = []
		with open('/home/gigra/payment_terms.csv') as cnt:
			_logger.info("READING TERMS")
			crdr = csv.reader(cnt, delimiter=';', quotechar='\"')   
			for c in crdr:
				if c[0] == "ID":
					continue
				vals = {
					'code':c[0],
					'desc': c[2],
				}
				terms.append(vals)
			_logger.info("...done")
		for t in terms:
			t_id = self.pool.get('account.payment.term').search(cr, uid, [("name", "=", t['code'])], context=None)
			if not t_id:
				self.pool.get('account.payment.term').create(cr, uid, {'name':t['code'], 'note': t['desc']}, context=None)
				
		return True
		
	def import_products_from_csv(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)
		product_ids = self.pool.get('product.template').search(cr, uid, [], context=None)
		_logger.info("***********%s " % len(product_ids))
		self.pool.get('product.template').write(cr, uid, product_ids, {'taxes_id': [1], 'supplier_taxes_id':[2]}, context=None)
		
		
		return True
	def TERMSSimport_products_from_csv(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)
		with open('/home/gigra/terms_sea.csv') as csvfile:
			crdr = csv.reader(csvfile, delimiter=';', quotechar='\"')
			for c in crdr:
				code = c[5].split("_")
				t_id = code[len(code) -1]
				client = c[0].split("_")
				c_id = client[len(client) -1]
				vat = c[4]
				if c_id == "id":
					continue
				
				client_id = self.pool.get('res.partner').search(cr, uid, [("name", "=", c[2])], context=None) 
				try:
					if client_id:
						for cl in client_id:
							client = self.pool.get('res.partner').browse(cr, uid, cl, context=None)
							client.property_payment_term = int(t_id)
							client.vat = vat
						_logger.info("SUCESS: %s" % client)
						continue
					_logger.error("CANT FIND CLIENT")
				except:
					_logger.error("++++++++++ERROR: %s" % c[0])
					
					
					
				
				
		
		return True 
	def TERMSZWEBimport_products_from_csv(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)
		acc = []
		with open('/home/gigra/account.csv') as cnt:
			_logger.info("READING ACCOUNTS")
			crdr = csv.reader(cnt, delimiter=';', quotechar='\"')   
			for c in crdr:
				vals = {
					'name':c[37],
					'term': c[40],
				}
				acc.append(vals)
			_logger.info("...done")
		
		for a in acc:
			c_id = self.pool.get('res.partner').search(cr, uid, [("name", "=", a['name'])], context=None)
			if c_id:
				up_id = self.pool.get('res.partner').write(cr, uid, c_id[0], {'property_payment_term': a['term']}, context=None)
				_logger.info("**** %s" % up_id)
		return True
	def PRICELISTimport_products_from_csv(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)
		prices = []
		with open('/home/gigra/sea_pricelist.csv') as cnt:
			_logger.info("READING PRICELISTS")
			crdr = csv.reader(cnt, delimiter=',', quotechar='\"')   
			for c in crdr:
				vals = {
					'name':c[1],
					'default_code': c[2],
					'list_price': c[3]
				}
				prices.append(vals)
			_logger.info("...done")
		product_ids = self.pool.get('product.template').search(cr, uid, [], context=None)
		products = self.pool.get('product.template').browse(cr, uid, product_ids, context=None)
		done = []
		for p in products:
			for x in prices:
				if x['default_code'] == p.default_code:
					p.list_price = float(x['list_price'])
					done.append({'name':p.name, 'default_code': p.default_code, 'list_price': p.list_price})
		with open('opt/odoo/done.csv', 'wb') as df:
			writer = csv.writer(df, delimiter=',',quotechar='|', quoting=csv.QUOTE_MINIMAL)
			for d in done:
				writer.writerow([d['default_code']] + [d['list_price']])
			
		return True
	def SDAimport_products_from_csv(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)
 
		craw = []
		araw = []
		notes = []
		adraw  = []
		acc_add = []
		with open('/home/gigra/contacts.csv') as cnt:
			_logger.info("READING CONTACTS")
			crdr = csv.reader(cnt, delimiter=';', quotechar='\"')   
			for c in crdr:
				craw.append(c)
			_logger.info("...done")
		with open('/home/gigra/account.csv') as acc:
			_logger.info("READING ACCOUNTS")
			ardr = csv.reader(acc, delimiter=';', quotechar='\"')   
			for a in ardr:
				araw.append(a)
			_logger.info("...done")
        #with open('/home/gigra/notes.csv') as nt:
            #_logger.info("READING NOTES")
            #nrdr = csv.reader(nt, delimiter=';', quotechar='\"')   
            #for n in nrdr:
            #   notes.append(n)
            #_logger.info("...done")
		with open('/home/gigra/addresses.csv') as add:
			_logger.info("READING ADDRESSES")
			nrdr = csv.reader(add, delimiter=';', quotechar='\"')   
			for ad in nrdr:
				adraw.append(ad)
			_logger.info("...done")
		with open('/home/gigra/acc_add.csv') as add:
			_logger.info("READING ADDRESSES")
			nrdr = csv.reader(add, delimiter=';', quotechar='\"')   
			for ad in nrdr:
				acc_add.append(ad)
			_logger.info("...done")
		addresses = []
		for a in adraw:
			for x in acc_add:
				if x[1] == a[0]:
					addresses.append({'client_id': x[0], 'id': a[0], 'street':a[1], 'city': a[5], 'country_id':a[7], 'state':a[19], 'zip':a[22]})
					break
 
		contacts = []
		clients = []
		counter = 0
		for a in araw:
			if a[37] == "NAME":
				continue
			desc = ''
            #for n in notes:
                #if n[11] == a[0]:
                    #if len(desc)>1:
                        #desc += " --- "
                    #desc += n[18] + " - " + n[5]
            
            #address = None
			address = []
			addressCounter = 0
			for xa in addresses:
				if xa['client_id'] == a[0]:
					addressCounter +=1
					address.append(xa)

			try:
				_logger.info("****//// %s" % a[37])
				cl_id = self.pool.get('res.partner').search(cr, uid, [("name", "=", a[37])], context=context)[0]
				for adr in address:
					if cl_id:
						
						street = adr['street']
						city = adr['city']
						country_id = adr['country_id']
						zip_code = adr['zip']
						if len(street) < 4:
							street=''
						if country_id == "\\N":
							country_id = ''
						if city == "\\N":
							city = ''
						if zip_code == "\\N":
							zip_code = ''
						if country_id:
							cnt_id = self.pool.get('res.country').search(cr, uid, [('code', '=', country_id)], context=None)[0]
						if self.pool.get('res.partner').search(cr, uid, [("street", "=", street), ("city", "=", city), ("zip", "=", zip_code)], context=context):
							_logger.info("ADDRESS EXISTS: %s" % adr)
							continue

						
						vals = {
							'name': a[37] + " secondary address",
							'street': street,
							'city': city,
							'country_id': cnt_id,
							'zip': zip_code,
							'parent_id':cl_id,
							'is_company': False
						}
						_logger.info("******- %s" % vals)
						cr_id = self.pool.get('res.partner').create(cr, uid, vals, context=None)
						if cr_id:
							_logger.info("CREATED")
						else:
							_logger.info("NOT CREATED")
					else:
						_logger.info("***client does not exist %s" % a[37])
				counter +=1
			except:
				_logger.warning("ERROR")
				continue
			continue
		_logger.info(counter)
        
		return True

	def XXXXimport_products_from_csv(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)
		with open('/home/gigra/main.csv', 'rb') as csvfile:
			reader = csv.reader(csvfile, delimiter=',', quotechar='"')
			counter = 0
			for row in reader:
				_logger.warning("******************")
				_logger.warning(row)
				
				counter +=1

			

				try:
					vals = {
						'name': row[0],
						'default_code': row[1],
						'description': row[2],
						'list_price': float(row[3]),
						'categ_id': row[4],
						#'image': row[5]
					}
					_logger.warning(vals)
					self.pool.get('product.template').create(cr, uid, vals, context=None)
					print "***************"
					print "Name: " + row[1]
					print "Int. code:" + row[0]
					print "Desc: " + row[2]
					print "Price: " + row[3]
					print "Category: " + row[4]
					if row[5]:
						print "Has image: YES"
					else:
						print "Has image: NO"
				except:
					_logger.error("*****************ERROR*******************")
					continue;

			print "LENGTH IS: " + str(counter)
		return True

	def XXXXimport_products_from_csv(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)
		with open('/home/gigra/buy_images.csv', 'rb') as csvfile:
			reader = csv.reader(csvfile, delimiter=',', quotechar='"')
			counter = 0
			for row in reader:
				_logger.warning("******************")
				_logger.warning(row)
				
				counter +=1

				

				if True:
					pro = self.pool.get('product.template').search(cr, uid, [("name", "=", row[0])], context=None)
					self.pool.get('product.template').write(cr, uid, pro, {'image': row[1]}, context=None)
					_logger.warning(pro)
					
					#print "***************"
					#print "Name: " + row[1]
					#print "Int. code:" + row[0]
					#print "Desc: " + row[2]
					#print "Price: " + row[3]
					#print "Category: " + row[4]
					#if row[5]:
					#	print "Has image: YES"
					#else:
					#	print "Has image: NO"

			print "LENGTH IS: " + str(counter)
		return True

	def XXimport_products_from_csv(self, cr, uid, ids, context=None):
		products = []
		reference = []
		with open('/home/gigra/reference.csv', 'rb') as ref:
			reader = csv.reader(ref, delimiter=',', quotechar='|')

			for x in reader:
				vals ={
					'by': x[0],
					'ft': x[1]
				}
				reference.append(vals)


		with open('/home/testserver/main.csv', 'rb') as csvfile:
			reader = csv.reader(csvfile, delimiter=',', quotechar='|')
		
			counter = 0
			
			for row in reader:
				vals = {
						'name': row[1],
						'default_code': row[0],
						'description': row[2],
						'list_price': float(row[3]),
						'categ_id': int(row[4]),
						'image': row[5]
				}
				products.append(vals)
		final_products = []
		for p in products:
				

				if p['list_price'] != 1 and p['categ_id'] > 1:
					img = 'no img'
					for x in products:
						if x['name'] == p['name'] and x['image'] != False:
							p['image'] = x['image']
							img = p['image'][:10]
							break
					for z in reference:
						if z['br'] == p['name']:
							p['default_code'] = z['ft']
					#print p['name'] + " " + p['description'][:10] + " " + p['categ_id'] + " " + str(p['list_price']) + img
					#self.pool.get('product.template').create(cr, uid, p, context=None)
					final_products.append(p)
					
					counter +=1

					#self.pool.get('product.template').create(cr, uid, vals, context=None)
					#print "***************"
					#print "Name: " + row[1]
					#print "Int. code:" + row[0]
					#print "Desc: " + row[2]
					#print "Price: " + row[3]
					#print "Category: " + row[4]
					#if row[5]:
					#	print "Has image: YES"
					#else:
					#	print "Has image: NO"
		with open('/home/testserver/bright_final.csv', 'wb') as csvfile:
			writer = csv.writer(csvfile, delimiter=',',quotechar='|', quoting=csv.QUOTE_MINIMAL)
			
			for p in final_products:
				try:
					writer.writerow([p['default_code']] + [p['name']] + [p['description']] + [p['list_price']] + [p['categ_id']] + [p['image']])
				except:
				
					continue

								

		print "LENGTH IS: " + str(counter)
		return True
#*****************************END INTRUDER********************************
	def export_invoice(self,increment_id, items, cs, context=None):
		_logger = logging.getLogger(__name__)
		_logger.warning("------------------- %s" % cs)
		_logger.warning("------------------- %s" % items)
		return _export_invoice(increment_id, items, cs)
	def _export_shipment(self, increment_id, items, tracking_no, cs, contex=None):
		_logger = logging.getLogger(__name__)
		_logger.warning("------------------- %s" % cs)
		_logger.warning("------------------- %s" % items)
		_logger.warning("------------------- %s" % tracking_no)
		return _export_shipment(increment_id, items,tracking_no, cs)
	
	def cron_import_orders(self, cr, uid, ids=1, context=None ):
		try:
			self.import_orders(self, cr, uid, ids, context=context) 
			self.pool.get('cron.log').create(cr, uid, {'name':'Magento Order Import', 'description': "Cron Succeded", 'status':0, 'date': datetime.datetime.now()}, context=None)

		except:
			self.pool.get('cron.log').create(cr, uid, {'name':'Magento Order Import', 'description': "Cron failed", 'status':1, 'date': datetime.datetime.now()}, context=None)
		
	
	def import_orders(self, cr, uid, ids, context = None):
				_logger = logging.getLogger(__name__)
				_logger.info("In Mageto Import Orders")
				for record in self.browse(cr, uid, ids, context=context):
					r = record

				cs = {
					'location': r.mage_location,
					'port': r.mage_port,
					'user': r.mage_user,
					'pwd': r.mage_pwd
				}
				magento = MagentoAPI(cs['location'], cs['port'], cs['user'], cs['pwd'])
				orders = magento.sales_order.list()
				print "Order count %s" % len(orders)
				for order in orders:
							print order['increment_id']
							o = magento.sales_order.info(order['increment_id'])
												
							
							inc_id = order['increment_id']
							exist_ids = self.pool.get('sale.order').search(cr, uid, [('magento_id', '=', inc_id)], context=context)
							if len(exist_ids) > 0:
								print order['increment_id']
								print exist_ids[0]
								print "Order exists already"
								_logger.warning("ORDER ALREADY EXISTS: %s ************" % exist_ids[0])
								continue
							
							
							if o['status_history'][0]['status'] != 'pending':
								continue

							
							payment = o['payment']['method']
							print "PAYMENT METHOD: " + payment

							if payment == 'cashondelivery':
								pm_id = 3
							elif payment == 'paypal':
								pm_id = 6
							elif payment == 'saved_cc':
								pm_id = 1
							else:
								pm_id = 5
							
							print "PARTNER ID CHECK"
							print o['customer_id']
							pid = self.pool.get('res.partner').search(cr, uid, [('magento_id', '=', o['customer_id'])], context=context)
							if not pid:
								country_ids = self.pool.get('res.country').search(cr, uid, [("code", "=", o['shipping_address']['country_id'])], context=None)
								country_id = False
								if country_ids:
									country_id = country_ids[0]
								par_vals = {
									'name': order['billing_firstname'],
									'email': order['customer_email'],
									'name': o['shipping_address']['firstname'],
									'street': o['shipping_address']['street'],
									'zip': o['shipping_address']['postcode'],
									'city': o['shipping_address']['city'],
									'country_id': country_id,
									'sale_warn': 'no-message',
									'purchase_warn': 'no-message',
									'picking_warn': 'no-message',
									'invoice_warn': 'no-message',
									'property_account_receivable':938,
									'property_account_payable':993,
									'notify_email':'always',
									'magento_id': o['customer_id']
								}
								partner_id = self.pool.get('res.partner').create(cr, uid, par_vals, context=context)
							else:
								partner_id = pid[0]
							
							payment_term = 2
							method_obj = self.pool.get('payment.method')
							if method_obj:
								method = method_obj.browse(cr, uid, pm_id, context=context)
								
								if method.payment_term_id:
									payment_term = method.payment_term_id.id

							company_ids = self.pool.get('res.company').search(cr, uid, [], context=None)
							shipping_partner = partner_id
							if o['shipping_address']:
								
								shipping_address = o['shipping_address']
								print shipping_address
							if shipping_address:
								print "there is shipping address"
								shipp_ids = self.pool.get('res.partner').search(cr, uid, [("parent_id", "=", partner_id), ("type", "=", "delivery")], context=None)
								
								found = False
								if shipp_ids:
									shipp = self.pool.get('res.partner').browse(cr, uid, shipp_ids, context=None)[0]
									print shipp.name
									print "inside has shipp"
									found = False
									for s in shipp:
										if int(shipping_address['address_id']) == s.magento_address_id:
											shipping_partner = s.id
											found = True
											print "found matching shipping address"
								if not found:
									print "inside does not have shipp"
									shipp_country_ids = self.pool.get('res.country').search(cr, uid, [("code", "=", o['shipping_address']['country_id'])], context=None)
									shipp_country_id = False
									if shipp_country_ids:
										shipp_country_id = shipp_country_ids[0]
									par_vals = {
										'name': shipping_address['firstname'],
										'street': shipping_address['street'],
										'zip': shipping_address['postcode'],
										'city': shipping_address['city'],
										'country_id': shipp_country_id,
										'sale_warn': 'no-message',
										'parent_id': partner_id,
										'type': 'delivery',
										'purchase_warn': 'no-message',
										'picking_warn': 'no-message',
										'invoice_warn': 'no-message',
										'property_account_receivable':938,
										'property_account_payable':993,
										'notify_email':'always',
										'magento_id': o['customer_id']
									}
									shipping_partner = self.pool.get('res.partner').create(cr, uid, par_vals, context=context)
									print "creating new shipping address"

							print shipping_partner

							company = company_ids[0]
							order_tmp = self.pool.get('sale.order')
							vals = {
									'partner_id': partner_id,
									'amount_tax': float(o['base_tax_amount']),
									'amount_untaxed': float(o['subtotal_incl_tax'])-float(o['base_tax_amount']),
									'pricelist_id': 1,
									'amount_total': float(o['subtotal_incl_tax']),
									#'name': so_name,
									'partner_invoice_id': partner_id,
									'partner_shipping_id': shipping_partner,
									'order_policy': 'manual',
									'picking_policy': 'direct',
									'warehouse_id': 1,
									'create_uid': 1,
									'user_id': 1,
									'company_id': company,
									'payment_method_id': pm_id,
									'workflow_process_id':1,
									'magento_id': order['increment_id'],
									#'procurement_group_id': self.pool.get('procurement.group').create(cr, uid, {}, context=context)
									'payment_term': payment_term

							}

							so_lines = []
							order_id = order_tmp.create(cr, uid, vals, context)

							print "ORDER CREATED WITH ID: " + str(order_id)
							for ol in o['items']:
										product_template_id = int(ol['sku'])
										pro_ids = self.pool.get('product.product').search(cr, uid, [('product_tmpl_id', '=', product_template_id)], context=context)
										if len(pro_ids) > 0:
											pro_id = pro_ids[0]
										else:
											print "**********CANT FIND %s" % product_template_id
											_logger.warning("**********CANT FIND %s" % product_template_id)
											continue
											
										line = {
											"name": ol['name'],
											"magento_id": ol['quote_item_id'],
											"product_uom": 1,
											"product_uos_qty": ol["qty_ordered"],
											"price_unit": float(ol["original_price"]),
											"product_uom_qty": float(ol["qty_ordered"]),
											"order_partner_id": partner_id,
											"order_id": order_id, 
											"product_id": pro_id,
											"product_template": product_template_id,
											"delay": 0,
											"route_id": 7, #Dropshipping
											"salesman_id": 1,
										}
										print "WROTE LINE"
										print line["magento_id"]
										so_lines.append(line)
							if 'shipping_amount' in o and o['shipping_amount']:
								amount = float(o['shipping_amount'])
								shipping_cost = {
									'name': 'Shipping fee',
									'product_uos_qty': 1,
									'product_uom': 1,
									'price_unit': amount,
									'order_partner_id': partner_id,
									'order_id': order_id,
									'delay': 0,
									'route_id': 7,
									'salesman_id':1
								}
								so_lines.append(shipping_cost)

							for s in so_lines:
										order_line = self.pool.get('sale.order.line')
										order_line.create(cr, uid, s, context)
				r.so_imported = datetime.datetime.now()

def _export_invoice(increment_id, items, cs):
	magento = MagentoAPI(cs['location'], cs['port'], cs['user'], cs['pwd'])

	return magento.sales_order_invoice.create(increment_id, items)

		
def _create_cron(self, cr, uid, name, tech_name, function, interval, interval_type):
		cr_vals = {
			'active': True,
			'display_name': name,
			'function': function,
			'interval_number': interval,
			'interval_type': interval_type,
			'model': 'magento_sync',
			'name': tech_name,
			'numbercall': -1,
			'priority': 1
		}

		return self.pool.get('ir.cron').create(cr, uid, cr_vals, context=None)
def _export_shipment(increment_id, items, tracking_no, cs):
	shippment_id = magento.sales_order_shipment.create(increment_id, items)
	tracking_id = magento.sales_order_shipment.addTrack(shippment_id, 'usps', "GLS", tracking_no)
	return shippment_id
def _export_categories(self, cr, uid, cs, instant_category=None):
	_logger  = logging.getLogger(__name__)
	magento = MagentoAPI(cs['location'], cs['port'], cs['user'], cs['pwd'])
	record = self.pool.get('magento_sync').browse(cr, uid, 1, context=None)
	if not record:
		print "Cannot get current record"
		return False

	cats_ids = self.pool.get('product.category').search(cr, uid, [("id", ">=", record.root_category), ("do_not_publish_mage", "=", False)], context=None)
	
	odoo_cats = self.pool.get('product.category').browse(cr, uid, [instant_category], context=None)
	
	odoo_cats = self.pool.get('product.category').browse(cr, uid, cats_ids, context=None)
	if instant_category and instant_category not in cats_ids:
		return True
	print len(odoo_cats)

	#GET MAGENTO CATEGORY COLLECTION
	mage_cats_raw = magento.catalog_category.tree()
	
	mage_cats = _sort_categories(mage_cats_raw)
	special_root = False
	#i_cat = self.pool.get('product.category').browse(cr, uid, instant_category, context=None)
	for c in odoo_cats:#i_cat if i_cat else odoo_cats:
		
		if c.mage_root == True:
			special_root = True
			add_category(self, cr, uid, c.parent_id.id, 1, mage_cats, odoo_cats, cs)
			break

	if not special_root:
		add_category(self, cr, uid, record.root_category, 2, mage_cats, odoo_cats, cs)


	to_remove_ids = self.pool.get('product.category').search(cr, uid, [("do_not_publish_mage", "=", True), ("magento_id", ">", 0)], context=None)
	print "To remove"
	print len(to_remove_ids)
	for to_remove in self.pool.get('product.category').browse(cr, uid, to_remove_ids, context=None):
		print to_remove.name
		_remove_cat(to_remove.magento_id, cs)
		to_remove.magento_id = 0
		children = odoo_get_children(self, cr, uid, to_remove.id, context=None)
		print children
		for ch in self.pool.get('product.category').browse(cr, uid, children, context=None):
			print ch.name
			ch.magento_id = 0
	"""
	if False:
		
			#REMOVING CATS
			cats_ids = self.pool.get('product.category').search(cr, uid, [("id", ">=", record.root_category), ("do_not_publish_mage", "=", False)], context=None)
			odoo_cats = self.pool.get('product.category').browse(cr, uid, cats_ids, context=None)
			mage_cats_raw = magento.catalog_category.tree()
		
			mage_cats = _sort_categories(mage_cats_raw)
			_logger.info("***********len odoo: %s" % len(odoo_cats))
			_logger.info("***********len mage: %s" % len(mage_cats))

			for m in mage_cats:
				try:
				

					_logger.warning("-----------MageCat:%s" % m['id'])
					if int(m['id']) > 2:
						_logger.warning("m is > 2 - %s" % m['id'])
						found = False
						
						for z in odoo_cats:
							if m['id'] == z.magento_id:
								found = True
								break

						if not found:
							print m['name']
							_logger.warning("***********REMOVING CAT: %s" % m['id'])
							_remove_cat(m['id'], cs)
							not_found_id = self.pool.get('product.category').search(cr, uid, [("magento_id", "=", m['id'])], context=None)
							self.pool.get('product.category').write(cr, uid, not_found_id, {'magento_id':0}, context=None)
							if False:
								children = [m['id']] 
								result = True
								while result:
									found = False
									for ch in children:
										for c in odoo_cats:
											if c['parent_id'] and c['parent_id'][0] == ch and c['id'] not in children:
												children.append(c['id'])
												found = True
							
									if not found:
										break
								self.pool.get('product.category').write(cr, uid, children, {'magento_id':0}, context=None)
				except:
					_logger.warning("ERROR REMOVING: %s" % m)
					trm_id = self.pool.get('product.category').search(cr, uid, [("magento_id", "=", m['id'])], context=None)
					self.pool.get('product.category').write(cr, uid, trm_id, {'magento_id':0}, context=None)
						
					"""
	return True

def _remove_cat(mage_id, cs):
	magento = MagentoAPI(cs['location'], cs['port'], cs['user'], cs['pwd'])
	return magento.catalog_category.delete(mage_id)

def odoo_get_children(self, cr, uid, start, context=None):
		
		p_id = [start]
		master = []
		while p_id:
			temp = []
			for p in p_id:
				#print p
				#print type(p)
				children = self.pool.get('product.category').search(cr, uid, [("parent_id", "=", p)], context=None)
				for c in children:
					temp.append(c)
			for t in temp:
				#print temp, t
				master.append(t)
			time.sleep(3)
			p_id = temp
			
		print master
		return master
	#END TEST

def add_category(self, cr, uid, odoo_parent, mage_parent, mage_cats, odoo_cats, cs):
	_logger  = logging.getLogger(__name__)
	is_added = False
	for c in odoo_cats:
		
		if c.parent_id.id == odoo_parent:
			_logger.warning("******MATCH: %s" % c.name)
			print "mage id_on_odoo: %s" % c.magento_id
			if c.do_not_publish_mage:
				active = 0
			else:
				active = 1
			res = _add_category(self, cr, uid, c.id, c.name, mage_parent,c.magento_id, active, cs)
			is_added = res['success']
			if is_added:
				add_category(self, cr, uid, c.id, res['parent_id'], mage_cats, odoo_cats, cs)

	
	return True

def _add_category(self, cr, uid, odoo_id, name, parent, mage_id, active, cs):
	magento = MagentoAPI(cs['location'], cs['port'], cs['user'], cs['pwd'])
	#*******URL KEY********
	_logger  = logging.getLogger(__name__)
	category = {
		'name': name,
		'is_active': active,
		'include_in_menu':1,
		'position': 1,
		'available_sort_by': ['name'],
		'default_sort_by': 'name',
	}
	if not mage_id:
		_logger.warning("************IN NEW %s*********" % category)
		print "in new"
		cat_id = magento.catalog_category.create(parent, category, '')
		self.pool.get('product.category').write(cr, uid, odoo_id, {'magento_id': cat_id}, context=None)
		print "CREATED CATEGORY WITH ID: %s" % cat_id
		#_translate_category(self, cr, uid, cat_id, name, cs)
		return {'success': True, 'parent_id': cat_id}
	else:
		_logger.warning("************IN UPDATE %s*********" % category)
		print "in update"
		cat_id = mage_id
		updated = magento.catalog_category.update(cat_id, category, '')
		#_translate_category(self, cr, uid, cat_id, name, cs)
		if updated:
			return {'success': True, 'parent_id': cat_id}
	print "******in _add_category********"
	print parent, category

def _translate_category(self, cr, uid, cat_id, name,  cs):
	magento = MagentoAPI(cs['location'], cs['port'], cs['user'], cs['pwd'])
	stores = ['en_us']
	
	for store in stores:
		#continue *///////////////////////////REMOVE FOR TRANSLATIONS TO WORK//////////////////////////////*
		trans_ids = self.pool.get('ir.translation').search(cr, uid, [("src", "ilike", store)], context=None)
		if not trans_ids:
			continue 
		trans_id = trans_ids[0]
		trans = self.pool.get("ir.translation").browse(cr, uid, trans_id, context=None)
		category = {
			'name': trans.value,
		}
		is_updated = magento.catalog_category.update(cat_id, category, store)
		print is_updated

	return True

def _export_products(self, cr, uid, full, cs, instant_product=None, qty=None):
	magento = MagentoAPI(cs['location'], cs['port'], cs['user'], cs['pwd'])


	_logger = logging.getLogger(__name__)
	_logger.warning("********CS IS: %s" % cs)
	record = self.pool.get('magento_sync').browse(cr, uid, 1, context=None)
	if not record:
		_logger.warning("Cannot get current record")
		return False

	
	root_cat = record.root_category
	last_update = record.products_exported
	
	if not instant_product:

		product_ids1 = self.pool.get('product.template').search(cr, uid, [("categ_id.do_not_publish_mage", "=", False)], context=None) # , ("do_not_publish_mage", "!=", True)
		
		product_ids2 = self.pool.get('product.template').search(cr, uid, [("do_not_publish_mage", "=", True)], context=None)
		
		product_ids = [item for item in product_ids1 if item not in product_ids2]
		products = self.pool.get('product.template').browse(cr, uid, product_ids, context=None)
		_logger.warning("**********************PRODUCT COUNT: %s" % len(products))
		
		if not full:
			ps = []
			for p in products:
				if p.__last_update > last_update:
					ps.append(p)

			products = ps
			_logger.warning("*******PRODUCTS WITH LAST UPDATE %s" % len(products))

		if not products:
			_logger.warning("**************************** NO PRODUCTS TO EXPORT")
			return True
	else:
		products = self.pool.get('product.template').browse(cr, uid, instant_product, context=None)

	
	#GET MAGENTO CATEGORY COLLECTION
	mage_cats_raw = magento.catalog_category.tree()
	
	
	mage_cats = _sort_categories(mage_cats_raw)
	counter = 0
	_logger.warning("**************************** PRODUCT COUNT: %s" % len(products))
	
	_logger.info('ping0 - getting attribute set')
	attr_set = magento.catalog_product_attribute_set.list()[0]
	_logger.info('ping0.2 - done getting attribute set')
	
	for p in products:
		try:
			#Benchmark
			starttime = datetime.datetime.now()
			counter +=1
			tran_ids = self.pool.get('ir.translation').search(cr, uid, [("lang", "=", "it_IT"), ('res_id', '=', p.id), ('name', '=', 'product.template,description')], context=None)
			translated_description = None
			if tran_ids:
				trans = self.pool.get('ir.translation').browse(cr, uid, tran_ids, context=None)
				translated_description = trans.value
			_logger.warning("******************* %s" % p.name)
			#p.magento_id = None
			sku = p.id
			name = p.name	
			desc = translated_description or p.description
			if p.oem_code:
				desc += " OEM CODE: %s" % p.oem_code
			short_desc = translated_description or p.description
			price = p.list_price
			tax_class_id = 0 #none
			visibility = 4 #catalog, search
			product_status = 1 #enabled
			websites = [1]
			#CATEGORIES
			
			if not p.categ_id.magento_id:
				_logger.warning("**********NOT SYNCING - NO CATEGORY ON MAGENTO: %s******************" % p.name)
				continue
			odoo_cat_mage_id = p.categ_id.magento_id
			
			mage_cat_ids = []
			
			for mc in mage_cats:
				
				if mc['id'] == odoo_cat_mage_id:
					mage_cat_ids.append(mc['id'])
					#_logger.warning("FOUND MATCHING CAT: " + mc['name'])
					_add_parents(mc['parent_id'], mage_cats, mage_cat_ids)
					#_logger.warning("******FINAL CATEGORY ARRAY IS: %s ******************" % mage_cat_ids)
					break
			
			urlkey = '/'
			for key in reversed(mage_cat_ids):
				for mc in mage_cats:
					if key == mc['id']:
						urlkey += mc['name']
						urlkey += '/'
			if len(urlkey)>1:
				urlkey += name
			else:
				urlkey = None

			#_logger.warning("******** URLKEY: %s" % urlkey)
			

			if len(mage_cat_ids) == 0:
				#print "Cant put to any category - putting to root!"
				mage_cat_ids.append(2)
			
			
			
			product = {
				'categories': mage_cat_ids,
				'websites': websites,
				'name': name,
				'description': desc,
				'short_description': short_desc,
				'status': product_status,
				'visibility': visibility,
				'price': price,
				'tax_class_id': tax_class_id,
				'url_key': urlkey,
				'weight': p.weight or 1,
				'stock_data': {
					'qty': qty or p.qty_available,
					'is_in_stock': 1,
					'use_config_manage_stock': 0,
					'manage_stock': 1,
					'min_qty': 0,
					'use_config_min_sale_qty':0,
					'min_sale_qty': 0,
					'use_config_max_sale_qty':0,
					'max_sale_qty': 9999,
					'notify_stock_qty': 0
					
				}

			}
			mi = None
			if p.image:
					print "%s has image" % p.name
					mi = {
						'file': {
							'content': p.image,
							'mime': 'image/jpeg',
							'name': p.default_code
						},
						'label': p.name,
						'position': 1,
						'types': ['thumbnail', 'small_image', 'image'],
						'exclude': 0,
						'remove':0
					}
			
			if True:
				#If failed to store locally, try to get over ws
				mage_id = p.magento_id if p.magento_id else _get_mage_id(self, cr, uid, p.id, magento)
				_logger.info("**********%s" % mage_id)
				if not mage_id:
					#_logger.info("************in new****************")

					product_id = magento.catalog_product.create('simple', attr_set['set_id'], sku, product)
					p.magento_id = product_id
					_logger.warning("PRODUCT EXPORTED TO MAGENTO WITH ID %s" % p.magento_id)
					if mi:
						image_mage = magento.catalog_product_attribute_media.create(p.magento_id, mi, '', 'productId')
						print image_mage
					
				else:
					#_logger.info(p.description)
					#_logger.info("***********in update*************")
					is_updated = magento.catalog_product.update(p.magento_id, product, '', 'productId')
					if is_updated:
						images_on_mage = magento.catalog_product_attribute_media.list(p.id, '', 'sku')
						print images_on_mage
						if len(images_on_mage) > 0:
							for i in images_on_mage:
								magento.catalog_product_attribute_media.remove(p.magento_id, i['file'], 'productId')
						if mi:
							image_mage = magento.catalog_product_attribute_media.create(p.magento_id, mi, '', 'productId')
							print image_mage
						_logger.warning("PRODUCT UPDATED TO MAGENTO WITH ID %s" % p.magento_id)
			
			mi = None
			#Benchmark
			endtime = datetime.datetime.now()
			_logger.info("***DURATION %s - %s, %s" % (starttime, endtime, starttime-endtime))
		except:
			e = sys.exc_info()[0]
			t = sys.stderr
			z = traceback.format_exc()
			_logger.warning("***********ERROR: %s " % e)
			_logger.warning(t) 
			_logger.warning(z)
			#raise osv.except_osv(_(e), _(str(t)+ "\n" + str(z)))
			continue


	return True

def _update_product_stock_mage(cs, id, qty):
	magento = MagentoAPI(cs['location'], cs['port'], cs['user'], cs['pwd'])
	product = {
				'stock_data': {
					'qty': qty,
					'is_in_stock': 1,
					'use_config_manage_stock': 0,
					'manage_stock': 1,
					'min_qty': 0,
					'use_config_min_sale_qty':0,
					'min_sale_qty': 0,
					'use_config_max_sale_qty':0,
					'max_sale_qty': 9999,
					'notify_stock_qty': 0
					
				}
	}
	return magento.catalog_product.update(id, product, '', 'productId')

def _delete_product_from_mage(cs, id):
		magento = MagentoAPI(cs['location'], cs['port'], cs['user'], cs['pwd'])
		try:
			magento.catalog_product.delete(id)
		except:
			return False
		return True
	
def _get_mage_id(self, cr, uid, sku, magento):
	_logger = logging.getLogger(__name__)
	_logger.info(sku)
	try:
		res = magento.catalog_product.info(sku,'', '', 'sku')
		if res['product_id']:
			self.pool.get('product.template').write(cr, uid, sku,{'magento_id':res['product_id']}, context=None)
			return res['product_id']
	except:
		return None

def _add_parents(cat_id, mage_cats, mage_cat_ids):
	if cat_id == 1:
		return True
	for c in mage_cats:
		if cat_id == c['id']:
			mage_cat_ids.append(cat_id)
			return _add_parents(c['parent_id'], mage_cats, mage_cat_ids)
	return True

cats = []
def _sort_categories(mage_cats):
	cats.append({'name': mage_cats['name'], 'parent_id': int(mage_cats['parent_id']), 'level': int(mage_cats['level']), 'parent_name': 'none', 'id': int(mage_cats['category_id'])})
	_get_children(mage_cats['children'], mage_cats['name'])
	return cats

def _get_children(ch_list, parent_name):
	
	for child in ch_list:
		cats.append({'name': child['name'], 'parent_id': int(child['parent_id']), 'level': int(child['level']), 'parent_name': parent_name, 'id': int(child['category_id'])})
		if len(child['children']) > 0:
			_get_children(child['children'], child['name'])

	return True

def _add_categories(op, mp, mcats, cats):
		counter = 0
		print "in new cat"
		for c in cats:
			if c.parent_id.id == op:
				isnew = True
				print "is new: " + str(isnew)
				if c.magento_id:
					isnew = False

				parent_added = False
				if isnew:
					parent_added = add_category(c.name, mp, '')
					counter += 1
				else:
					parent_added = True
				
				if parent_added:
					pid = 2
					for m in mcats:
						print "********************************************"
						print m


class product_category(models.Model):
	_inherit = "product.category"

	magento_id = fields.Integer(string="MagentoID")

	def XXcreate(self, cr, uid, vals, context=None):
		try:
			res = super(product_category, self).create(cr, uid, vals, context=context)
		except: 
			raise osv.osv_except(_('Error'), _('Theres been an error'))
		print 'cat create %s' % res
		r = self.pool.get('magento_sync').search(cr, uid, [], context=None)
		if r:
			
			ins = self.pool.get('magento_sync').browse(cr, uid, r, context=None)[0]
			cs = {
				'location': ins.mage_location,
				'port': ins.mage_port,
				'user': ins.mage_user,
				'pwd': ins.mage_pwd
			}
			print vals
			if 'do_not_publish_mage' not in vals or not vals['do_not_publish_mage']:
				print "new export"
				#_export_categories(self, cr, uid, cs, res)
		return res

	def XXwrite(self, cr, uid, ids, vals, context=None):
		print 'cat write'
		
		res = super(product_category, self).write(cr, uid, ids, vals, context=context)
		r = self.pool.get('magento_sync').search(cr, uid, [], context=None)
		if r:
			ins = self.pool.get('magento_sync').browse(cr, uid, r, context=None)[0]
			cs = {
				'location': ins.mage_location,
				'port': ins.mage_port,
				'user': ins.mage_user,
				'pwd': ins.mage_pwd
			}
		print vals
		for cat in self.browse(cr, uid, ids, context=None):
			if 'do_not_publish_mage' not in vals or not vals['do_not_publish_mage']:
				if 'magento_id' not in vals or vals['magento_id'] > 0:
					print "updating"
					#_export_categories(self, cr, uid, cs, cat.id)
			elif vals['do_not_publish_mage']:
				print "removing"
				print cat
				_remove_cat(cat.magento_id, cs)
				cat.magento_id = None
		return res

	def Xunlink(self, cr, uid, ids, context=None):
		print 'cat unlink'
		r = self.pool.get('magento_sync').search(cr, uid, [], context=None)
		if r:
			print "has row"
			ins = self.pool.get('magento_sync').browse(cr, uid, r, context=None)[0]
			cs = {
				'location': ins.mage_location,
				'port': ins.mage_port,
				'user': ins.mage_user,
				'pwd': ins.mage_pwd
			}
		for cat in self.browse(cr, uid, ids, context=None):
			if cat.magento_id:
				_remove_cat(cat.magento_id, cs)
		return super(product_category, self).unlink(cr, uid, ids, context=context)

	

class product_template(models.Model):
	_inherit = "product.template"
	

	magento_id = fields.Integer(sting="Magento ID")
	do_not_publish_mage = fields.Boolean(string="Do not publish on magento")

	def write(self, cr, uid, ids, vals, context=None):
		print "IN WRITE %s" % vals
		''' Store the standard price change in order to be able to retrieve the cost of a product template for a given date'''
		if isinstance(ids, (int, long)):
			ids = [ids]
		if 'uom_po_id' in vals:
			new_uom = self.pool.get('product.uom').browse(cr, uid, vals['uom_po_id'], context=context)
			for product in self.browse(cr, uid, ids, context=context):
				old_uom = product.uom_po_id
				if old_uom.category_id.id != new_uom.category_id.id:
					raise osv.except_osv(_('Unit of Measure categories Mismatch!'), _("New Unit of Measure '%s' must belong to same Unit of Measure category '%s' as of old Unit of Measure '%s'. If you need to change the unit of measure, you may deactivate this product from the 'Procurements' tab and create a new one.") % (new_uom.name, old_uom.category_id.name, old_uom.name,))
		if 'standard_price' in vals:
			for prod_template_id in ids:
				self._set_standard_price(cr, uid, prod_template_id, vals['standard_price'], context=context)
		res = super(product_template, self).write(cr, uid, ids, vals, context=context)
		if 'attribute_line_ids' in vals or vals.get('active'):
			self.create_variant_ids(cr, uid, ids, context=context)
		if 'active' in vals and not vals.get('active'):
			ctx = context and context.copy() or {}
			ctx.update(active_test=False)
			product_ids = []
			for product in self.browse(cr, uid, ids, context=ctx):
				product_ids += map(int, product.product_variant_ids)
			self.pool.get("product.product").write(cr, uid, product_ids, {'active': vals.get('active')}, context=ctx)

		#Export mage
		if 'description' not in vals and 'qty_available' not in vals and 'list_price' not in vals and 'name' not in vals and 'do_not_publish_mage' not in vals and 'image' not in vals and 'active' not in vals and 'categ_id' not in vals:
			print "returning"
			return res
		r = self.pool.get('magento_sync').search(cr, uid, [], context=None)
		if r:
			ins = self.pool.get('magento_sync').browse(cr, uid, r, context=None)[0]
			cs = {
				'location': ins.mage_location,
				'port': ins.mage_port,
				'user': ins.mage_user,
				'pwd': ins.mage_pwd
			}
			#get products changed
			products = self.browse(cr, uid, ids, context=None)
			for p in products:
				print "export from update"
				if not p.categ_id.do_not_publish_mage and not p.do_not_publish_mage and p.categ_id.magento_id:
					_export_products(self, cr, uid, True, cs, instant_product=p.id)
				elif p.magento_id:
					_delete_product_from_mage(cs, p.magento_id)
					p.magento_id = None
		return res

	def unlink(self, cr, uid, ids, context=None):
		print "in_unlink"
		products = self.browse(cr, uid, ids, context=None)
		print products
		res = super(product_template, self).unlink(cr, uid, ids, context=None)
		if True:
			r = self.pool.get('magento_sync').search(cr, uid, [], context=None)
			if r:
				ins = self.pool.get('magento_sync').browse(cr, uid, r, context=None)[0]
				cs = {
					'location': ins.mage_location,
					'port': ins.mage_port,
					'user': ins.mage_user,
					'pwd': ins.mage_pwd
				}
				for p in products:
					if p.magento_id:
						_delete_product_from_mage(cs, p.magento_id)
						
		return res


	def create(self, cr, uid, vals, context=None):
		print "IN NEW %s" % vals
		''' Store the initial standard price in order to be able to retrieve the cost of a product template for a given date'''
		vals['magento_id'] = 0
		product_template_id = super(product_template, self).create(cr, uid, vals, context=context)
		if not context or "create_product_product" not in context:
			self.create_variant_ids(cr, uid, [product_template_id], context=context)
		self._set_standard_price(cr, uid, product_template_id, vals.get('standard_price', 0.0), context=context)

		# TODO: this is needed to set given values to first variant after creation
		# these fields should be moved to product as lead to confusion
		related_vals = {}
		if vals.get('ean13'):
			related_vals['ean13'] = vals['ean13']
		if vals.get('default_code'):
			related_vals['default_code'] = vals['default_code']
		if related_vals:
			self.write(cr, uid, product_template_id, related_vals, context=context)
		
		r = self.pool.get('magento_sync').search(cr, uid, [], context=None)
		if r:
			ins = self.pool.get('magento_sync').browse(cr, uid, r, context=None)[0]
			cs = {
				'location': ins.mage_location,
				'port': ins.mage_port,
				'user': ins.mage_user,
				'pwd': ins.mage_pwd
			}
			p = self.browse(cr, uid, product_template_id, context=None)
			if not p.categ_id.do_not_publish_mage and not p.do_not_publish_mage:
				print "export from new"
				_export_products(self, cr, uid, True, cs, instant_product=product_template_id)

		return product_template_id

class SaleOrderLine(models.Model):
	_inherit = "sale.order.line"

	magento_id = fields.Integer(string="MagentoID")

class AccountInvoice(models.Model):
	_inherit = 'account.invoice'

	magento_id = fields.Integer(string="MagentoID")

class AccountInvoiceLine(models.Model):
	_inherit = 'account.invoice.line'

	magento_id = fields.Integer(string="MagentoID")

class res_partner(models.Model):
	_inherit = "res.partner"

	def simple_vat_check(self, cr, uid, country_code, vat_number, context=None):

		return True

class cron_log(models.Model):
	_name = "cron.log"

	name = fields.Char(string="Model")
	description = fields.Text(string="Description")
	date = fields.Datetime(stirng="Date")
	status =fields.Integer(string="Status")

class stock_change_product_qty(models.Model):
	_inherit = "stock.change.product.qty"

	def change_product_qty(self, cr, uid, ids, context=None):
		print "here"
		""" Changes the Product Quantity by making a Physical Inventory. """
		if context is None:
			context = {}

		inventory_obj = self.pool.get('stock.inventory')
		inventory_line_obj = self.pool.get('stock.inventory.line')

		for data in self.browse(cr, uid, ids, context=context):
			
			print data.product_id
			if data.new_quantity < 0:
				raise UserError(_('Quantity cannot be negative.'))
			if data.product_id.product_tmpl_id.magento_id:
				#export to magento
				r = self.pool.get('magento_sync').search(cr, uid, [], context=None)
				if r:
					ins = self.pool.get('magento_sync').browse(cr, uid, r, context=None)[0]
					cs = {
						'location': ins.mage_location,
						'port': ins.mage_port,
						'user': ins.mage_user,
						'pwd': ins.mage_pwd
					}
					_update_product_stock_mage(cs, data.product_id.magento_id, data.new_quantity)

			ctx = context.copy()
			ctx['location'] = data.location_id.id
			ctx['lot_id'] = data.lot_id.id
			if data.product_id.id and data.lot_id.id:
				filter = 'none'
			elif data.product_id.id:
				filter = 'product'
			else:
				filter = 'none'
			inventory_id = inventory_obj.create(cr, uid, {
				'name': _('INV: %s') % tools.ustr(data.product_id.name),
				'filter': filter,
				'product_id': data.product_id.id,
				'location_id': data.location_id.id,
				'lot_id': data.lot_id.id}, context=context)
			product = data.product_id.with_context(location=data.location_id.id, lot_id= data.lot_id.id)
			th_qty = product.qty_available
			line_data = {
				'inventory_id': inventory_id,
				'product_qty': data.new_quantity,
				'location_id': data.location_id.id,
				'product_id': data.product_id.id,
				'product_uom_id': data.product_id.uom_id.id,
				'theoretical_qty': th_qty,
				'prod_lot_id': data.lot_id.id
			}
			inventory_line_obj.create(cr , uid, line_data, context=context)
			inventory_obj.action_done(cr, uid, [inventory_id], context=context)
		return {}
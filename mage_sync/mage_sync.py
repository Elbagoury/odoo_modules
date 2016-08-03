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
import hashlib

class magento_pt_mapping(models.Model):
	_name = "magento.pt.mapping"

	name = fields.Char(string="Payment term magento")
	payment_term = fields.Many2one('payment.method', string="Payment method")



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
	default_user = fields.Many2one('res.users', string="Default user")
	mage_location = fields.Char(string="Mage location")
	mage_port = fields.Integer(default=80, string="Mage port")
	mage_user = fields.Char(string="Mage user")
	mage_pwd = fields.Char(string="Mage PWD")
	root_category = fields.Integer(string="Mage root cat")

	product_cron = fields.Many2one('ir.cron')
	customer_cron = fields.Many2one('ir.cron')
	orders_cron = fields.Many2one('ir.cron')
	categories_cron = fields.Many2one('ir.cron')

	auto_update_products = fields.Boolean(string="Automatic update of data")
	import_delivery_cost = fields.Boolean(string="Include delivery cost in orders")
	confirmation_email_template = fields.Many2one('email.template', string="Template for order confirmation")


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

	def compare_prices(self, cr, uid, ids, context=None):


		for record in self.browse(cr, uid, ids, context=context):
			r = record

		magento = MagentoAPI(r.mage_location, r.mage_port, r.mage_user, r.mage_pwd)
		product_ids = self.pool.get('product.template').search(cr, uid, [], context=None)
		products = self.pool.get('product.template').browse(cr, uid, product_ids, context=None)
		cnt = 0
		last = 0
		res = magento.catalog_product.list()
		mage_pros = []
		for r in res:
			p = magento.catalog_product.info(r['product_id'], '', '', 'productId')
			if p:
				mage_pros.append(p)


		for p in products:
				for x in mage_pros:
					if p.id == x['sku']:
						if not p.magento_id:
							p.magento_id = x['product_id']

					if p.list_price != float(x['price']):
						vals = {
							'product_id': p.id,
							'odoo_price': p.list_price,
							'mage_price': x['price'],
							'magento_instance': r.id
						}
						self.pool.get('magento.price.compare').create(cr, uid, vals, context=None)


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



	def cron_export_customers(self, cr, uid, ids=1, context=None):
		return export_customers(self, cr, uid, ids, context=None)
	def export_customers(self, cr, uid, ids, context = None, client_id=None):
			for record in self.pool.get('magento_sync').browse(cr, uid, ids, context=context):
				r = record
			_logger = logging.getLogger(__name__)
			magento = MagentoAPI(r.mage_location, r.mage_port, r.mage_user, r.mage_pwd)

			client_ids = self.pool.get('res.partner').search(cr, uid, [("sync_to_mage", "=", True), ("email", "!=", False), ("customer", "=", True),("city", "!=", False), ("zip", "!=", False),("street", "!=", False), ("phone", "!=", False), ('is_company', '=', True), ('active', '=', True)], context=None)
			if client_id:
				clients = self.pool.get('res.partner').browse(cr, uid, client_id, context=None)
			else:
				clients = self.pool.get('res.partner').browse(cr, uid, client_ids, context=None)
			_logger.warning("**********CUSTOMER COUNT: %s" % len(clients))
			counter = 0

			for c in clients:

				_logger.info("*****************CUSTOMER: %s - %s ** %s" % (c.name, c.magento_id, counter))
				pl = c.property_product_pricelist.mage_cat
				group_id = 1
				if pl:
					group_id = pl

				pwd = hashlib.md5("prova1").hexdigest()
				if c.mage_customer_pass:
					pwd = hashlib.md5(c.mage_customer_pass).hexdigest()
				c.email = c.email.lstrip()
				client = {
					'email': c.email,
					'firstname': c.name,
					'lastname': c.last_name or "-",

					'password_hash': pwd,
					'website_id': 1,
					'store_id': 1,
					'group_id':group_id
				}

				address = [[c, {
						'city': c.city,
						'company': c.name,
						'country_id': c.country_id.code,
						'firstname': c.name,
						'lastname': c.last_name or "-",
						'postcode': c.zip,
						'street': c.street,
						'telephone': c.phone or "000000",
						'is_default_billing': 1,
						'is_default_shipping': 1
					}]]
				shipp_ids = self.pool.get('res.partner').search(cr, uid, [("parent_id", "=", c.id), ("type", "=", "delivery")], context=None)
				if shipp_ids:
					shipp = self.pool.get('res.partner').browse(cr, uid, shipp_ids, context=None)
					for s in shipp:
						last_nm = c.last_name or "-"
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
							'telephone': s.phone or "000000",
							'is_default_shipping': 1,
							'is_default_billing': 0
							}]
						address.append(a)
				try:
					if not c.magento_id:


						try:
							c.magento_id = magento.customer.create(client)
						except:
							raise osv.except_osv(_("ERROR EXPORTING CLIENT"), _(traceback.format_exc()))

						for ad in address:
							ad[0].magento_address_id = magento.customer_address.create(c.magento_id, ad[1])


					else:
						try:
							is_updated = magento.customer.update(c.magento_id, client)
						except:
							raise osv.except_osv(_("ERROR EXPORTING CLIENT"), _(traceback.format_exc()))

						if is_updated and c.magento_address_id:
							for a in address:
								if a[0].magento_address_id:

									magento.customer_address.update(a[0].magento_address_id, a[1])
								else:

									a[0].magento_address_id = magento.customer_address.create(c.magento_id, a[1])

							for ma in magento.customer_address.list(c.magento_id):

								found = False
								for a in address:
									if int(ma['customer_address_id']) == a[0].magento_address_id:

										found = True
										break
								if not found:
									magento.customer_address.delete(ma['customer_address_id'])
				except:

					continue

                                counter += 1
				address = None

			r.customers_exported = datetime.datetime.utcnow()
			return True



	def export_pricelists(self, cr, uid, ids, context = None):
		_logger = logging.getLogger(__name__)
		product_ids = self.pool.get('product.template').search(cr, uid, [("categ_id.magento_id", ">", 0), ("do_not_publish_mage", "=", False)], context=None)
		products = self.pool.get('product.template').browse(cr, uid, product_ids, context=None)
		for record in self.browse(cr, uid, ids, context=context):
				r = record

		cs = {
			'location': r.mage_location,
			'port': r.mage_port,
			'user': r.mage_user,
			'pwd': r.mage_pwd
		}
		magento = MagentoAPI(cs['location'], cs['port'], cs['user'], cs['pwd'])

		cnt = 0
		last = 0
		limit = 0

		for p in products:
			cnt +=1
			if cnt - last == 500:
				_logger.info("PRICELIST EXPORT PROGRESS: %s" % cnt)
				last = cnt
				magento = MagentoAPI(cs['location'], cs['port'], cs['user'], cs['pwd'])


			_logger.info("EXPORTING PRICELIST FOR: %s (%s)" % (p.name, p.id))
			_export_pricelists(self, cr, uid, p, magento)

	def reindex(self, cr, uid, ids, context=None):
		for record in self.browse(cr, uid, ids, context=context):
				r = record

		cs = {
			'location': r.mage_location,
			'port': r.mage_port,
			'user': r.mage_user,
			'pwd': r.mage_pwd
		}

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

		#for c in cats:
		#	if c['id'] > 2:
		#		magento.catalog_category.delete(c['id'])



		return True

	def sync_ids_products(self, cr, uid, ids, context=None):
		product_ids = self.pool.get('product.template').search(cr, uid, [("categ_id.magento_id", ">", 0), ("do_not_publish_mage", "=", False)], context=None)
		products = self.pool.get('product.template').browse(cr, uid, product_ids, context=None)
		r = self.browse(cr, uid, ids, context=context)[0]

		cs = {
			'location': r.mage_location,
			'port': r.mage_port,
			'user': r.mage_user,
			'pwd': r.mage_pwd
		}
		cnt = 0
		total = len(products)
		magento = MagentoAPI(cs['location'], cs['port'], cs['user'], cs['pwd'])
		res = magento.catalog_product.list()
		for p in products:
			if not p.magento_id:
				for r in res:
					if str(r['sku'].strip()) == str(p.id):
						p.magento_id = r['product_id']

	def sync_ids_clients(self, cr, uid, ids, context=None):


		client_ids = self.pool.get('res.partner').search(cr, uid, [("sync_to_mage", "=", True), ("email", "!=", False), ("customer", "=", True),("city", "!=", False), ("zip", "!=", False),("street", "!=", False), ("phone", "!=", False), ('is_company', '=', True), ('active', '=', True)], context=None)
		clients = self.pool.get('res.partner').browse(cr, uid, client_ids, context=None)
		r = self.browse(cr, uid, ids, context=context)[0]

		cs = {
			'location': r.mage_location,
			'port': r.mage_port,
			'user': r.mage_user,
			'pwd': r.mage_pwd
		}
		cnt = 0
		total = len(clients)
		magento = MagentoAPI(cs['location'], cs['port'], cs['user'], cs['pwd'])
		res = magento.customer.list()
		for c in clients:
			for r in res:

				if r['email'].strip() == c.email.strip():

					c.magento_id = r['customer_id']

	def test_button(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)

		r = self.browse(cr, uid, ids, context=context)[0]

		cs = {
			'location': r.mage_location,
			'port': r.mage_port,
			'user': r.mage_user,
			'pwd': r.mage_pwd
		}
		magento = MagentoAPI(cs['location'], cs['port'], cs['user'], cs['pwd'])
		product_ids = self.pool.get('product.template').search(cr, uid, [('state', '!=', 'sellable')], context=None)

		_logger.info("PRODUCTS TO DEL %s" % len(product_ids))

		for p in product_ids:
			try:
				res = magento.catalog_product.delete(p, 'sku')
				_logger.info(res)
			except:
				_logger.info("DOES NOT EXIST %s" % p)
				continue



		return True
		res = magento.catalog_product.list()

		products = []
		for r in res:
			p = magento.catalog_product.info(r['product_id'], '', ['price'], 'productId')
			products.append(p)




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


	def export_invoice(self,increment_id, items, cs, context=None):

		return _export_invoice(increment_id, items, cs)
	def _export_shipment(self, increment_id, items, tracking_no, cs, contex=None):

		return _export_shipment(increment_id, items,tracking_no, cs)

	def cron_import_orders(self, cr, uid, ids=1, context=None ):
		try:
			_logger = logging.getLogger(__name__)
			_logger.info("ORDER IMPORT CRON STARTED *******************")
			self.import_orders(cr, uid, ids, context=context)
			_logger.info("PASSED *******************")
			self.pool.get('cron.log').create(cr, uid, {'name':'Magento Order Import', 'description': "Cron Succeded", 'status':0, 'date': datetime.datetime.now()}, context=None)

		except:
			e = sys.exc_info()[0]
			t = sys.stderr
			z = traceback.format_exc()
			_logger.warning("***********ERROR: %s " % e)
			self.pool.get('cron.log').create(cr, uid, {'name':'Magento Order Import', 'description': "FAIL", 'status':1, 'date': datetime.datetime.now()}, context=None)


	def import_orders(self, cr, uid, ids, context = None):
				_logger = logging.getLogger(__name__)

				for record in self.browse(cr, uid, ids, context=context):
					r = record
				user_id = r.default_user.id if r.default_user else 1
				cs = {
					'location': r.mage_location,
					'port': r.mage_port,
					'user': r.mage_user,
					'pwd': r.mage_pwd
				}
				magento = MagentoAPI(cs['location'], cs['port'], cs['user'], cs['pwd'])
				orders = magento.sales_order.list()

				for order in orders:

							o = magento.sales_order.info(order['increment_id'])


							inc_id = order['increment_id']
							exist_ids = self.pool.get('sale.order').search(cr, uid, [('magento_id', '=', inc_id)], context=context)
							if len(exist_ids) > 0:


								continue


							if o['status_history'][0]['status'] != 'pending':
								continue

							#WHEN CONSIDERING MAGENTO - OFF
							payment = o['payment']['method']


							if payment == 'cashondelivery':
								pm_id = 3
							elif payment == 'paypal':
								pm_id = 6
							elif payment == 'saved_cc':
								pm_id = 1
							else:
								pm_id = 5


							pid = self.pool.get('res.partner').search(cr, uid, [('magento_id', '=', o['customer_id']), ('active', '=', True), ('is_company', '=', True)], context=context)
							if not pid:
								country_ids = self.pool.get('res.country').search(cr, uid, [("code", "=", o['shipping_address']['country_id'])], context=None)
								country_id = False
								if country_ids:
									country_id = country_ids[0]
								par_vals = {
									'name': order['billing_firstname'],
									'user_id': user_id,
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

							partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=None)[0]

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

							if shipping_address:

								shipp_ids = self.pool.get('res.partner').search(cr, uid, [("parent_id", "=", partner_id), ("type", "=", "delivery")], context=None)

								found = False
								if shipp_ids:
									shipp = self.pool.get('res.partner').browse(cr, uid, shipp_ids, context=None)[0]

									found = False
									for s in shipp:
										if int(shipping_address['address_id']) == s.magento_address_id:
											shipping_partner = s.id
											found = True

								if not found:

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
										'magento_id': o['customer_id'],
										'user_id': user_id
									}
									shipping_partner = self.pool.get('res.partner').create(cr, uid, par_vals, context=context)




							company = company_ids[0]
							order_tmp = self.pool.get('sale.order')
							vals = {
									'partner_id': partner_id,
									'amount_tax': float(o['base_tax_amount']),
									'amount_untaxed': float(o['subtotal_incl_tax'])-float(o['base_tax_amount']),
									'pricelist_id': partner.property_product_pricelist.id or 1,
									'amount_total': float(o['subtotal_incl_tax']),
									#'name': so_name,
									'partner_invoice_id': partner_id,
									'partner_shipping_id': shipping_partner,
									'order_policy': 'manual',
									'picking_policy': 'direct',
									'warehouse_id': 1,
									'create_uid': user_id,
									'user_id': user_id,
									'order_policy':'picking',
									'company_id': company,
									'note':o['comment'] if 'comment' in o else '',
									#'payment_method_id': pm_id,
									#'workflow_process_id':1,
									'magento_id': order['increment_id'],
									#'procurement_group_id': self.pool.get('procurement.group').create(cr, uid, {}, context=context)
									'payment_term': partner.property_payment_term.id

							}

							so_lines = []
							order_id = order_tmp.create(cr, uid, vals, context)


							for ol in o['items']:
										product_template_id = int(ol['sku'])
										pro_ids = self.pool.get('product.product').search(cr, uid, [('product_tmpl_id', '=', product_template_id)], context=context)
										if len(pro_ids) > 0:
											pro_id = pro_ids[0]
										else:

											_logger.warning("**********CANT FIND %s" % product_template_id)
											continue
										product = self.pool.get('product.product').browse(cr, uid, pro_id, context=None)[0]
										pricelist =  partner.property_product_pricelist or None
										discount_rate = 0
										if pricelist:

											if len(pricelist.version_id):
												version = pricelist.version_id[0]
												items = version.items_id
												qty = 0
												for item in items:
													if float(ol["qty_ordered"]) >= item.min_quantity and item.min_quantity >= qty:
														discount_rate = (item.price_discount * -1) * 100
														qty = item.min_quantity

										tax_id = product.product_tmpl_id.taxes_id[0].id if product.product_tmpl_id.taxes_id else 0
										line = {
											"name": product.description,
											"magento_id": ol['quote_item_id'],
											"product_uom": 1,
											"product_uos_qty": ol["qty_ordered"],
											"price_unit": float(ol["original_price"]),
											"product_uom_qty": float(ol["qty_ordered"]),
											"pricelist_discount": discount_rate,
											"order_partner_id": partner_id,
											"order_id": order_id,
											"product_id": pro_id,
											"product_template": product.product_tmpl_id.id,
											"delay": 0,
											#"route_id": 7, #Dropshipping
											"salesman_id": user_id,
											'tax_id': [[4,tax_id]]
										}

										so_lines.append(line)

							if 'shipping_amount' in o and o['shipping_amount'] and r.import_delivery_cost:
								amount = float(o['shipping_amount'])
								shipping_cost = {
									'name': 'Shipping fee',
									'product_uos_qty': 1,
									'product_uom': 1,
									'price_unit': amount,
									'order_partner_id': partner_id,
									'order_id': order_id,
									'delay': 0,
									#'route_id': 7,
									'salesman_id':user_id
								}
								so_lines.append(shipping_cost)

							for s in so_lines:
										order_line = self.pool.get('sale.order.line')
										order_line.create(cr, uid, s, context)

							self.pool.get('sale.order').signal_workflow(cr, uid, [order_id], 'order_confirm')

							email_template = r.confirmation_email_template
							if email_template:

								self.pool.get('email.template').send_mail(cr, uid, email_template.id, order_id)

				r.so_imported = datetime.datetime.now()

def _export_invoice(increment_id, items, cs):
	magento = MagentoAPI(cs['location'], cs['port'], cs['user'], cs['pwd'])
	o = magento.sales_order.info('200000060')

	res = magento.sales_order_invoice.create('200000060', [{'order_item_id': '28', 'qty':1}])

	return res


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

		return False

	cats_ids = self.pool.get('product.category').search(cr, uid, [("id", ">=", record.root_category), ("do_not_publish_mage", "=", False)], context=None)

	odoo_cats = self.pool.get('product.category').browse(cr, uid, [instant_category], context=None)

	odoo_cats = self.pool.get('product.category').browse(cr, uid, cats_ids, context=None)
	if instant_category and instant_category not in cats_ids:
		return True


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

	for to_remove in self.pool.get('product.category').browse(cr, uid, to_remove_ids, context=None):

		_remove_cat(to_remove.magento_id, cs)
		to_remove.magento_id = 0
		children = odoo_get_children(self, cr, uid, to_remove.id, context=None)

		for ch in self.pool.get('product.category').browse(cr, uid, children, context=None):

			ch.magento_id = 0

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

				children = self.pool.get('product.category').search(cr, uid, [("parent_id", "=", p)], context=None)
				for c in children:
					temp.append(c)
			for t in temp:

				master.append(t)

			p_id = temp


		return master
	#END TEST

def add_category(self, cr, uid, odoo_parent, mage_parent, mage_cats, odoo_cats, cs):
	_logger  = logging.getLogger(__name__)
	is_added = False
	for c in odoo_cats:

		if c.parent_id.id == odoo_parent:


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


		cat_id = magento.catalog_category.create(parent, category, '')
		self.pool.get('product.category').write(cr, uid, odoo_id, {'magento_id': cat_id}, context=None)

		#_translate_category(self, cr, uid, cat_id, name, cs)
		return {'success': True, 'parent_id': cat_id}
	else:


		cat_id = mage_id
		updated = magento.catalog_category.update(cat_id, category, '')
		#_translate_category(self, cr, uid, cat_id, name, cs)
		if updated:
			return {'success': True, 'parent_id': cat_id}


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


	return True
def _export_pricelists(self, cr, uid, product, magento):
	_logger = logging.getLogger(__name__)
	pl_ids = self.pool.get('product.pricelist').search(cr, uid, [("mage_cat", ">", 0)], context=None)
	pls = self.pool.get('product.pricelist').browse(cr, uid, pl_ids, context=None)

	res = []
	for p in pls:
		version = False
		for v in p.version_id:
			version = v

		categ_ids = {}

		categ = product.categ_id
		while categ:
			categ_ids[categ.id] = True
			categ = categ.parent_id
		categ_ids = categ_ids.keys()

		items = v.items_id


		for i in items:
			if i.min_quantity == 0:
				if i.categ_id.id and i.categ_id.id not in categ_ids:

					continue
				else:
					curr = {

						'group_id': p.mage_cat,
						'qty': i.min_quantity,
						'price': 1 + i.price_discount
					}

					res.append(curr)

			else:
				if i.categ_id.id and i.categ_id.id not in categ_ids:

					continue
				else:
					curr = {

						'group_id': p.mage_cat,
						'qty': i.min_quantity,
						'price': 1 + i.price_discount
					}
					res.append(curr)



	_logger.info("----- PRICELIST: %s" % res)

	#magento = MagentoAPI(cs['location'], cs['port'], cs['user'], cs['pwd'])

	groups = []
	tiers = []
	for r in res:
		if r['qty'] == 0:
			if True:#r['categ_id'] and r['categ_id'] == p_cid:
				mage_group = {
					'cust_group': r['group_id'],
					'website_id':'all',

					'price': product.list_price * r['price']
				}
				groups.append(mage_group)
		else:
			mage_tier = {
				'customer_group_id': r['group_id'],
				'website':'all',
				'qty': r['qty'],
				'price': product.list_price * r['price']
			}
			tiers.append(mage_tier)

	try:
		res = magento.catalog_product.update(product.id, {'group_price':groups, 'tier_price':tiers, 'price':product.list_price}, '', 'sku')
		return res
	except:
		return True


def _export_products(self, cr, uid, full, cs, instant_product=None, qty=None):
	magento = MagentoAPI(cs['location'], cs['port'], cs['user'], cs['pwd'])

	_logger = logging.getLogger(__name__)

	record = self.pool.get('magento_sync').browse(cr, uid, 1, context=None)
	if not record:
		_logger.warning("Cannot get current record")
		return False
	inital_value_auto = record.auto_update_products
	record.auto_update_products = False
	root_cat = record.root_category
	last_update = record.products_exported

	if not instant_product:

		product_ids = self.pool.get('product.template').search(cr, uid, [("categ_id.magento_id", ">", 0), ('state', 'not in', ['draft', 'obsolete']),("do_not_publish_mage", "=", False)], context=None) # , ("do_not_publish_mage", "!=", True)
		to_remove_ids = self.pool.get('product.template').search(cr, uid, ['|', ("categ_id.magento_id", "=", 0), ('categ_id.do_not_publish_mage', '=', True), ('state', 'in', ['draft', 'obsolete']),("do_not_publish_mage", "=", True)], context=None)
		to_remove = self.pool.get('product.template').browse(cr, uid, to_remove_ids, context=None)
		products = self.pool.get('product.template').browse(cr, uid, product_ids, context=None)


		for tr in to_remove:
			if tr.magento_id > 0:
				_logger.info("---_%s" % _remove_product(self, cr, uid, ids, tr, magento))

		if not full:
			ps = []
			for p in products:
				if p.__last_update > last_update:
					ps.append(p)

			products = ps
			_logger.warning("*******EXPORTING ONLY WITH LAST UPDATE")

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


	attr_set = magento.catalog_product_attribute_set.list()[0]

	cntx = 0
	last = 0
	#go = False
	for p in products:
		cntx +=1

		if cntx - last == 200:
			_logger.info("----------- %s" % cntx)
			last = cntx

		try:


			#If failed to store locally, try to get over ws
			mage_id = p.magento_id or None
			if not mage_id:
				mage_id = _get_mage_id(self, cr, uid, p.id, magento)
				p.magento_id = mage_id




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
			name_trans_id = self.pool.get('ir.translation').search(cr, uid, [("lang", "=", "it_IT"), ('res_id', '=', p.id), ('name', '=', 'product.template,name')], context=None)
			if name_trans_id:
				name_trans = self.pool.get('ir.translation').browse(cr, uid, name_trans_id, context=None)
				name = name_trans.value
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

					_add_parents(mc['parent_id'], mage_cats, mage_cat_ids)

					break

			urlkey = '&#47;'
			for key in reversed(mage_cat_ids):
				for mc in mage_cats:
					if key == mc['id']:
						urlkey += mc['name']
						urlkey += '/'
			if len(urlkey)>1:
				urlkey += name
			else:
				urlkey = None




			if len(mage_cat_ids) == 0:

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
					'notify_stock_qty': 0,
					'use_config_backorders': 0,
					'backorders': 2
				}

			}
			mi = None
			if p.image:

					mi = {
						'file': {
							'content': p.image,
							'mime': 'image/jpeg',
							'name': p.name or "Image"
						},
						'label': p.name.replace('/', '-'),
						'position': 1,
						'types': ['thumbnail', 'small_image', 'image'],
						'exclude': 0,
						'remove':0
					}

			if True:

				if not mage_id:


					product_id = magento.catalog_product.create('simple', attr_set['set_id'], sku, product)
					p.magento_id = product_id
					_logger.warning("PRODUCT EXPORTED TO MAGENTO WITH ID %s" % p.magento_id)

					if mi:
						image_mage = magento.catalog_product_attribute_media.create(p.magento_id, mi, '', 'productId')


				else:

					is_updated = magento.catalog_product.update(p.magento_id, product, '', 'productId')
					if is_updated:
						images_on_mage = magento.catalog_product_attribute_media.list(p.id, '', 'sku')

						if len(images_on_mage) > 0:
							for i in images_on_mage:
								magento.catalog_product_attribute_media.remove(p.magento_id, i['file'], 'productId')
						if mi:
							image_mage = magento.catalog_product_attribute_media.create(p.magento_id, mi, '', 'productId')

						_logger.warning("PRODUCT UPDATED TO MAGENTO WITH ID %s" % p.magento_id)


				_export_pricelists(self, cr, uid, p.magento_id, p, cs)

			mi = None

			endtime = datetime.datetime.now()

		except:
			e = sys.exc_info()[0]
			t = sys.stderr
			z = traceback.format_exc()
			_logger.warning("***********ERROR: %s " % e)
			_logger.warning(t)
			_logger.warning(z)

			continue

	record.auto_update_products = inital_value_auto
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
def _remove_product(self, cr, uid, product, magento):
	try:
		res = magento.catalog_product.delete(product.magento_id, 'productId')
		return res
	except:
		return False
	return True
def _get_mage_id(self, cr, uid, sku, magento):
	_logger = logging.getLogger(__name__)

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

		for c in cats:
			if c.parent_id.id == op:
				isnew = True

				if c.magento_id:
					isnew = False

				parent_added = False
				if isnew:
					parent_added = add_category(c.name, mp, '')
					counter += 1
				else:
					parent_added = True

				#if parent_added:
				#	pid = 2
				#	for m in mcats:



def _export_category(self, cr, uid, cat_id):
	_logger  = logging.getLogger(__name__)

	record = self.pool.get('magento_sync').browse(cr, uid, 1, context=None)


	if not record:

		return False

	root_category = record.root_category

	cs = {
			'location': record.mage_location,
			'port': record.mage_port,
			'user': record.mage_user,
			'pwd': record.mage_pwd
	}
	cat = self.pool.get('product.category').browse(cr, uid, cat_id, context=None)[0]
	magento = MagentoAPI(cs['location'], cs['port'], cs['user'], cs['pwd'])

	if cat.do_not_publish_mage or cat.id < root_category:

		return False


	if not cat.parent_id.magento_id:
		parent_category = 2
	else:
		parent_category = cat.parent_id.magento_id

	children = odoo_get_children(self, cr, uid, cat.id, context=None)

	to_insert = [cat.id] + children



	for ch in self.pool.get('product.category').browse(cr, uid, to_insert, context=None):
		if not ch.parent_id.magento_id:
			parent_category = 2
		else:
			parent_category = ch.parent_id.magento_id
		category = {
			'name': ch.name,
			'is_active': 1,
			'include_in_menu':1,
			'position': 1,
			'available_sort_by': ['name'],
			'default_sort_by': 'name',
		}
		mcid = magento.catalog_category.create(parent_category, category, '')
		ch.magento_id = mcid

	return True

def _update_category(self, cr, uid, mage_id, name):
	_logger  = logging.getLogger(__name__)

	record = self.pool.get('magento_sync').browse(cr, uid, 1, context=None)


	if not record:

		return False

	root_category = record.root_category

	cs = {
			'location': record.mage_location,
			'port': record.mage_port,
			'user': record.mage_user,
			'pwd': record.mage_pwd
	}

	magento = MagentoAPI(cs['location'], cs['port'], cs['user'], cs['pwd'])

	category = {
			'name': name,
			'is_active': 1,
			'include_in_menu':1,
			'position': 1,
			'available_sort_by': ['name'],
			'default_sort_by': 'name',
	}

	mcid = magento.catalog_category.update(mage_id, category, '')


	return True
class product_category(models.Model):
	_inherit = "product.category"

	magento_id = fields.Integer(string="MagentoID")

	def create(self, cr, uid, vals, context=None):
		try:
			res = super(product_category, self).create(cr, uid, vals, context=context)
		except:
			raise osv.osv_except(_('Error'), _('Theres been an error'))

		r = self.pool.get('magento_sync').search(cr, uid, [], context=None)
		if r:

			ins = self.pool.get('magento_sync').browse(cr, uid, r, context=None)[0]
			cs = {
				'location': ins.mage_location,
				'port': ins.mage_port,
				'user': ins.mage_user,
				'pwd': ins.mage_pwd
			}

			if 'do_not_publish_mage' not in vals or not vals['do_not_publish_mage']:

				_export_category(self, cr, uid, res)
		return res

	def write(self, cr, uid, ids, vals, context=None):


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

		for cat in self.browse(cr, uid, ids, context=None):
			if 'name' not in vals and 'do_not_publish_mage' not in vals:

				continue
			if 'do_not_publish_mage' not in vals or not vals['do_not_publish_mage']:
				if cat.magento_id:

					_update_category(self, cr, uid, cat.magento_id, cat.name)
				else:
					_export_category(self, cr, uid, cat.id)
			elif vals['do_not_publish_mage']:
				if not cat.magento_id:

					continue

				children = odoo_get_children(self, cr, uid, cat.id, context=None)

				_remove_cat(cat.magento_id, cs)
				cat.magento_id = None
				self.pool.get('product.category').write(cr, uid, children, {'magento_id': 0}, context=None)
		return res

	def unlink(self, cr, uid, ids, context=None):

		r = self.pool.get('magento_sync').search(cr, uid, [], context=None)
		if r:

			ins = self.pool.get('magento_sync').browse(cr, uid, r, context=None)[0]
			cs = {
				'location': ins.mage_location,
				'port': ins.mage_port,
				'user': ins.mage_user,
				'pwd': ins.mage_pwd
			}
		for cat in self.browse(cr, uid, ids, context=None):
			if cat.magento_id:

				children = odoo_get_children(self, cr, uid, cat.id, context=None)

				_remove_cat(cat.magento_id, cs)
				cat.magento_id = None
				self.pool.get('product.category').write(cr, uid, children, {'magento_id': 0}, context=None)
		return super(product_category, self).unlink(cr, uid, ids, context=context)

class MagentoPriceCompare(models.Model):
	_name = 'magento.price.compare'

	product_id = fields.Many2one('product.template', string="Product")
	odoo_price = fields.Float(string="Odoo price")
	mage_price = fields.Float(string="Magento price")
	magento_instance = fields.Integer(string="Instance ID")


class product_template(models.Model):
	_inherit = "product.template"


	magento_id = fields.Integer(sting="Magento ID")
	do_not_publish_mage = fields.Boolean(string="Do not publish on magento")

	def write(self, cr, uid, ids, vals, context=None):

		res = super(product_template, self).write(cr, uid, ids, vals, context=context)
		if 'magento_id' in vals:
			return res
		if 'description' not in vals and 'qty_available' not in vals and 'list_price' not in vals and 'name' not in vals and 'do_not_publish_mage' not in vals and 'image' not in vals and 'active' not in vals and 'categ_id' not in vals:
			return res


		r = self.pool.get('magento_sync').search(cr, uid, [], context=None)
		if r:

			ins = self.pool.get('magento_sync').browse(cr, uid, r, context=None)[0]
			if not ins.auto_update_products:
				return res
			cs = {
				'location': ins.mage_location,
				'port': ins.mage_port,
				'user': ins.mage_user,
				'pwd': ins.mage_pwd
			}
			#get products changed
			products = self.browse(cr, uid, ids, context=None)
			for p in products:

				if not p.categ_id.do_not_publish_mage and not p.do_not_publish_mage and p.categ_id.magento_id:
					_export_products(self, cr, uid, True, cs, instant_product=p.id)
				elif p.magento_id:
					_delete_product_from_mage(cs, p.magento_id)
					p.magento_id = None
		return res

	def unlink(self, cr, uid, ids, context=None):

		products = self.browse(cr, uid, ids, context=None)

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

		vals['magento_id'] = 0
		product_template_id = super(product_template, self).create(cr, uid, vals, context=context)
		try:
			r = self.pool.get('magento_sync').search(cr, uid, [], context=None)
			if r:

				ins = self.pool.get('magento_sync').browse(cr, uid, r, context=None)[0]
				if not ins.auto_update_products:
					return product_template_id
				cs = {
					'location': ins.mage_location,
					'port': ins.mage_port,
					'user': ins.mage_user,
					'pwd': ins.mage_pwd
				}
				p = self.browse(cr, uid, product_template_id, context=None)
				if not p.categ_id.do_not_publish_mage and not p.do_not_publish_mage:
					_export_products(self, cr, uid, True, cs, instant_product=product_template_id)
		except:
			return product_template_id
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
		res = super(stock_change_product_qty, self).change_product_qty(cr, uid, ids, context=context)
		for data in self.browse(cr, uid, ids, context=context):
			if data.product_id.product_tmpl_id.magento_id:

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
		return res

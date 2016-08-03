from openerp import fields, models, api, _
import datetime
import os
import sys
import logging
from openerp.osv import osv

from optparse import OptionParser
import json


sys.path.insert(0, '%s/../' % os.path.dirname(__file__))

from common import dump

import ebaysdk
from ebaysdk.utils import getNodeText
from ebaysdk.exception import ConnectionError
from ebaysdk.trading import Connection as Trading

import base64
from binascii import hexlify
import getpass
import os
import select
import socket
import sys
import time
import traceback
from paramiko.py3compat import input
import logging



import paramiko
from magento_api import MagentoAPI

class ebay(models.Model):
	_name = 'ebay'

	name = fields.Char()
	app_id = fields.Char()
	dev_id = fields.Char()
	cert_id = fields.Char()
	token_id = fields.Text()
	products_exported_date = fields.Datetime()
	orders_imported_date = fields.Datetime()
	orders_cron = fields.Many2one('ir.cron')
	import_categories_date = fields.Datetime()
	messages_synced_date = fields.Datetime()
	messages_cron = fields.Many2one('ir.cron')
	default_user = fields.Many2one('res.users', string="Default user")
	cat_version = fields.Integer()
	ebay_pricelist_id = fields.Many2one('product.pricelist')
	ebay_warehouse_id = fields.Many2one('stock.warehouse')
	ebay_price_formula = fields.Float()
	ebay_shipping_cost = fields.Float()
	ebay_shipping_additional = fields.Float()
	ebay_payment_inst = fields.Char()
	ebay_stock_limit = fields.Integer()
	ebay_listing_dur = fields.Selection((('Days_7', '7 days'), ('Days_30', '30 days'), ('GTC', 'Good `Till Canceled')))
	ebay_template_id = fields.Many2one('ebay.template')
	ebay_item_loc = fields.Char()
	ebay_paypal_email = fields.Char()
	ebay_payment_term_id = fields.Many2one('account.payment.term', string="Default payment term")
	ebay_account_position = fields.Many2one('account.fiscal.position', string="Default fiscal position")
	ebay_goods_description = fields.Many2one('stock.picking.goods_description', string="Default goods description")
	ebay_carriage_condition = fields.Many2one('stock.picking.carriage_condition', string="Default carriage condition")
	ebay_transportation_reason = fields.Many2one('stock.picking.transportation_reason', string="Default transportation reason")
	ebay_transportation_method = fields.Many2one('stock.picking.transportation_method', string="Default transportation method")
	default_categ = fields.Many2one('product.category', string="Default product category")

	override_default = fields.Boolean()

	def get_shipping_services(self, cr, uid, ids, context=None):
		instance_id = self.pool.get('ebay').search(cr,uid, [], context=None)
		i = self.browse(cr, uid, ids, context=None)
		cert = i.cert_id
		dev = i.dev_id
		app = i.app_id
		tok = i.token_id
		(opts, args) = init_options()
		services = _get_services(opts, cert, dev, app, tok)
		for s in services:
			self.pool.get('ebay.shipping.service').create(cr, uid, s, context=None)
		return True
	def remove_product(self, cr, uid, ids, context=None):
		instance_id = self.pool.get('ebay').search(cr,uid, [], context=None)
		i = self.browse(cr, uid, instance_id, context=None)
		i = i[0]
		cert = i.cert_id
		dev = i.dev_id
		app = i.app_id
		tok = i.token_id
		(opts, args) = init_options()

		product_ids = ids
		if len(product_ids) > 1:
			raise osv.except_osv(_("Warning"), _("You can remove only one product at a time"))
		product = self.pool.get('product.template').browse(cr, uid, product_ids, context=None)[0]
		ebay_ids = product.ebay_id
		if not ebay_ids:
			product.ebay_sync = False
			return True
		eids = [e.ebay_id for e in ebay_ids]
		res = removeFromEbay(opts, cert, dev, app, tok, eids)

		for zeid in product.ebay_id:
			zeid.unlink()
		product.sync_ebay = False
		for np in product.name_parts:
			np.ebay_id = None
			np.suffix = None

	def complete_sale(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)
		instance_id = self.pool.get('ebay').search(cr,uid, [], context=None)
		i = self.browse(cr, uid, instance_id, context=None)
		i = i[0]
		cert = i.cert_id
		dev = i.dev_id
		app = i.app_id
		tok = i.token_id
		(opts, args) = init_options()

		invoice_ids = ids
		if len(invoice_ids) > 1:
			raise osv.except_osv(_("Warning"), _("You can complete sale for one invoice at a time"))
		invoice = self.pool.get('account.invoice').browse(cr, uid, invoice_ids, context=None)[0]
		invoice_lines = invoice.invoice_line
		gls_parcels = invoice.gls_parcel
		if not gls_parcels:
			raise osv.except_osv(_("Warning"), _("No tracking numbers available"))
		gls_parcel = gls_parcels[0]
		for line in invoice_lines:
			if line.ebay_item_id and line.ebay_order_id:
				item = {
					'ItemID': line.ebay_item_id,
					'OrderID': line.ebay_order_id,
					'Shipment': {
						'ShipmentTrackingDetails':{
							'ShipmentTrackingNumber': "CE %s" % gls_parcel.numero_spedizione,
							'ShippingCarrierUsed': invoice.carrier_id.carrier_id.name
						}
					},
					'Shipped': True
				}
				ack = completeSale(opts, cert, dev, app, tok, item)
				if ack == "Success":
					invoice.tracking_sent_to_ebay = True


	def export_products(self, cr, uid, ids, product_id=None,context=None):
		_logger = logging.getLogger(__name__)
		(opts, args) = init_options()
		current_record = None
		for record in self.browse(cr, uid, ids, context=context):
			current_record = record

		lst_up = current_record.products_exported_date
		prd_tmp = self.pool.get('product.template')
		if product_id:
			pro_ids = product_id
		else:

			pro_ids = prd_tmp.search(cr, uid, [('ebay_sync', '=', True)], context=context)

		_logger.warning("***EBAY: Product count: %s********" % len(pro_ids))
		if pro_ids:
			for pro in prd_tmp.browse(cr, uid, pro_ids, context=context):
				_logger.warning("*******INSIDE PRODUCT %s ************" % pro.name)

				if pro.main_name_part:

					cnt = 0
					for pn in pro.name_parts:
						cnt += 1
						suffix = "_ZW" + str(cnt)
						code = pro.name
						desc = "%s  %s" % (pro.main_name_part, pn.name)
						code += suffix
						_logger.warning("********* INSERTING PRODUCT %s ******** %s" % (code, len(pro.name_parts)))
						item = save_product(pro, code, desc, lst_up, current_record)
						if "Error" in item:
							raise osv.except_osv(_(code), _(item['Error']))

						if not pn.ebay_id:
							ebay_id, ebay_date = addItem(current_record, item)
							_logger.info("Product has no ebay_id, inserting new")
							if ebay_id and ebay_date:
								pn.suffix = suffix
								pn.ebay_id = ebay_id
								self.pool.get('ebay.ids').create(cr, uid, {'product_id': pro.id, 'ebay_id': ebay_id})
								pro.ebay_date_added = ebay_date

						else:
							_logger.info("This one has ebay_id %s" % pn.ebay_id)
							addItem(current_record, item, ebay_id=pn.ebay_id)
				elif len(pro.description) <= 80:
					_logger.warning("********* INSERTING PRODUCT %s  NO NAME PARTS********" % pro.name)
					item = save_product(pro, pro.name, pro.description, lst_up, current_record)
					if "Error" in item:
						raise osv.except_osv(_(code), _(item['Error']))
					if pro.ebay_id:
						ebay_id = pro.ebay_id[0].ebay_id
						addItem(current_record, item, ebay_id=ebay_id)
					else:

						ebay_id, ebay_date = addItem(current_record, item)

						if ebay_id and ebay_date:
							self.pool.get('ebay.ids').create(cr, uid, {'product_id': pro.id, 'ebay_id': ebay_id})
							pro.ebay_date_added = ebay_date
				else:
					_logger.warning("********* Skipping %s ********" % pro.name)
					continue

		current_record.products_exported_date = datetime.datetime.now()

		return True
	def create_messages_cron(self, cr, uid, ids, context=None):
		r = self.browse(cr, uid, ids, context=None)
		r.messages_cron = _create_cron(self, cr, uid, "Read ebay messages", "ebay_read_messages", "read_messages", 5, "minutes")
		return True

	def create_orders_cron(self, cr, uid, ids, context=None):
		r = self.browse(cr, uid, ids, context=None)
		r.orders_cron = _create_cron(self, cr, uid, "Import ebay orders", "ebay_import_orders", "cron_import_orders", 10, "minutes")
		return True

	def read_messages(self, cr, uid, ids=2, context=None, only_new=True):
		_logger = logging.getLogger(__name__)
		r = self.browse(cr, uid, ids, context=context)
		cert = r.cert_id
		dev = r.dev_id
		app = r.app_id
		tok = r.token_id
		(opts, args) = init_options()

		messages_hdrs = _get_messages_hdr(opts, cert, dev, app, tok)
		if not messages_hdrs['Messages']:
			return True
		to_get = []
		to_update = []
		msg_ids = []
		for m in messages_hdrs["Messages"]["Message"]:
			exists = self.pool.get('ebay.message').search(cr, uid, [("message_id", "=", m["MessageID"])], context=None)
			if exists:
				to_update.append({'msg': m, 'odoo_id': exists})
			else:
				to_get.append(m)

			msg_ids.append(m['MessageID'])


		resps = _get_messages(opts, cert, dev, app, tok, to_get)

		for m in resps:

			vals = {
				'content':m['content'],
				'flagged':True if m['header']["Flagged"] == "true" else False,

				'item_id':m['header']['ItemID'] if 'ItemID' in m['header'] else '',
				'message_id': m['header']["MessageID"],
				'external_message_id': m['header']['ExternalMessageID'] if 'ExternalMessageID' in m['header'] else None,

				'is_read': True if m['header']["Read"] == "true" else False,
				'rcv_date': m['header']["ReceiveDate"],
				'replied':True if m['header']["Replied"] == "true" else False,
				'sender_name':m['header']['Sender'],

				'name': m['header']['Subject'],

				'ebay_instance_id': r.id
			}
			msg_id = self.pool.get('ebay.message').create(cr, uid, vals, context=None)
			_logger.info("Created: %s - %s" % (msg_id, m['header']['ReceiveDate']))

		if not only_new:
			#UPDATE EXISTING
			for x in to_update:
				vals = {
					'flagged':True if x["msg"]["Flagged"] == "true" else False,
					'is_read':True if x["msg"]["Read"] == "true" else False,
					'replied':True if x["msg"]["Replied"] == "true" else False,

				}
				self.pool.get('ebay.message').write(cr, uid, x['odoo_id'], vals, context=None)
				_logger.info("Updated: %s" % x['odoo_id'])


			#DELETE MSGS DELETED EXTERNALY
			odoo_msg_ids = self.pool.get('ebay.message').search(cr, uid, [], context=None)
			odoo_collection = [{'message_id': x.message_id, 'id': x.id} for x in self.pool.get('ebay.message').browse(cr, uid, odoo_msg_ids, context=None)]
			for m in odoo_collection:
				if m['message_id'] not in msg_ids:
					self.pool.get('ebay.message').unlink(cr, uid, [m['id']], context=None)
					_logger.info("Deleted: %s" % m)

		r.messages_synced_date = datetime.datetime.now()
		return True

	def cron_import_orders(self, cr, uid, ids=2, context=None):
		try:
			_logger = logging.getLogger(__name__)
			_logger.info("EBAY ORDER IMPORT CRON STARTED *******************")
			self.import_orders(cr, uid, ids, context=context)
			_logger.info("EBAY ORDER IMPORT CRON FINISHED *******************")
		except:
			e = sys.exc_info()[0]

			_logger.warning("***********ERROR IMPORTING EBAY ORDERS: %s " % e)

	def import_orders(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)
		_logger.info("STARTING_IMPORT_ORDERS")
		#ids = self.pool.get('ebay').search(cr, uid, ids, [], context=None)
		r = self.browse(cr, uid, ids, context=context)
		if not r:
			_logger.warning("FATAL. COULD NOT RETRIEVE CONFIG")
			return False

		r = r[0]
		#GET ORDERS FROM EBAY
		cert = r.cert_id
		dev = r.dev_id
		app = r.app_id
		tok = r.token_id
		(opts, args) = init_options()
		orders= getOrders(opts, cert, dev, app, tok)


		#DEBUG - DEBUG - DEBUG
		with open('/opt/odoo/gigra_addons/ebay_connector/orders.txt', 'w') as outfile:
			json.dump(orders, outfile)

		res_par = self.pool.get('res.partner')
		pro_tmp = self.pool.get('product.template')

		ox = orders


		order_ids = []
		_logger.info("LEN OF ORDERS IS: %s" % len(ox))
		for o in ox:
			res = _import_order(self, cr, uid, ids, o, [r])
			if res:
				order_ids.append(res)
			else:
				continue


		if True:
			_logger.info("ORDER_IDS: %s" % order_ids)

			invoice_ids = []

			#AUTOMATIC PAYMENT _ NOT QUITE WORKING
			if False:
				for inv in self.pool.get('account.invoice').browse(cr, uid, invoice_ids, context=None):
					inv.signal_workflow('invoice_open')
					move = inv.move_id
					period_id = self.pool.get('account.voucher')._get_period(cr, uid)
					partner_id = self.pool.get('res.partner')._find_accounting_partner(inv.partner_id).id

					voucher_vals = {
						'partner_id': partner_id,
						'amount': inv.amount_total,
						'journal_id':9,
						'period_id':period_id,
						'account_id': 1028,
						'type': inv.type in ('out_invoice', 'out_refund') and 'receipt', #or payment
						'reference': inv.name
					}
					_logger.info("**** VOUCHER_DATA: %s" % voucher_vals)

					voucher_id = self.pool.get('account.voucher').create(cr, uid, voucher_vals, context=None)
					_logger.info("*** VOUCHER_ID: %s" % voucher_id)

					self.pool.get('account.voucher').write(cr, uid, [voucher_id], {'state': 'draft'}, context=None)
					double_check = 0
					for move_line in inv.move_id.line_id:
						if inv.type in ('out_invoice', 'out_refund'):
							if move_line.debit > 0.0:
								line_data = {
									'name': inv.number,
									'voucher_id': voucher_id,
									'move_line_id': move_line.id,
									'account_id': inv.account_id.id,
									'partner_id': partner_id,
									'amount_unreconciled': abs(move_line.debit),
									'amount_original': abs(move_line.debit),
									'amount': abs(move_line.debit),
									'type': 'cr'
								}
								#_logger.info("****** %s" % line_data)

								line_id = self.pool.get('account.voucher.line').create(cr, uid, line_data, context=None)
								double_check +=1
						else:
							if move_line.credit > 0.0:
								line_data = {
									'name': inv.number,
									'voucher_id' : voucher_id,
									'move_line_id' : move_line.id,
									'account_id' : inv.account_id.id,
									'partner_id' : partner_id,
									'amount_unreconciled': abs(move_line.credit),
									'amount_original': abs(move_line.credit),
									'amount': abs(move_line.credit),
									'type': 'dr',
								}
								line_id = self.pool.get('account.voucher.line').create(cr, uid, line_data, context=context)
								double_check += 1

					if double_check == 0:
						_logger.error("**** DID NOT CREATE ANY V LINES")
						raise osv.except_osv(_("Warning"), _("I did not create any voucher line"))
					elif double_check > 1:
						_logger.error("**** CREATED MORE THAT ONE V LINE")
						raise osv.except_osv(_("Warning"), _("I created multiple voucher line ??"))

					self.pool.get('account.voucher').button_proforma_voucher(cr, uid, [voucher_id], context=context)


		r.orders_imported_date = datetime.datetime.now()

		return True

	def _cancel_order(self, cert, dev, app, tok, order_line_item_ids):
		(opts, args) = init_options()
		api = Trading(debug=opts.debug, config_file=None, appid=app, token=tok,
                      certid=cert, devid=dev, warnings=True, timeout=20)

		for olid in order_line_item_ids:
			if olid:
				api.execute('AddDispute', {'DisputeExplanation': 'BuyerNoLongerWantsItem', 'DisputeReason': 'TransactionMutuallyCanceled', 'OrderLineItemID': olid})
				print api.response.json()
		return True

	def import_categories(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)
		category_tmp = self.pool.get('ebay.categories.line')
		r = self.browse(cr, uid, ids, context=context)
		cert = r.cert_id
		dev = r.dev_id
		app = r.app_id
		tok = r.token_id
		(opts, args) = init_options()
		categories = getCategories(opts, cert, dev, app, tok)
		_logger.info("******************* %s" % categories)
		version = categories['Version']

		result = True

		for cat in categories["CategoryArray"]["Category"]:
			match = category_tmp.search(cr, uid, [('name', '=', cat["CategoryName"])], context=context)
			if not match:
				vals = {
					'version_id': version,
					'categoryID': cat['CategoryID'],
					'name': cat['CategoryName'],
					'level': cat['CategoryLevel'],
					'parent': cat['CategoryParentID']
				}
				try:
					category_tmp.create(cr, uid, vals, context)
				except:
					result = False

		for record in self.browse(cr, uid, ids, context=context):
			record.import_categories_date = datetime.datetime.now()
			if version:
				record.cat_version = version

		return True

class ebay_incomplete_orders(models.Model):
	_name = "ebay.incomplete.orders"

	order_id = fields.Char(string="Order ebay ID")
	customer = fields.Char(string="Customer")
	date = fields.Datetime(string="Date ordered")
	total_amount = fields.Char(string="Total amount")
	payment_status = fields.Char(string="Payment status")

class ebay_name_parts(models.Model):
	_name = 'ebay.name.parts'

	np_id = fields.Integer()
	name = fields.Char(string="Other parts of name")
	ebay_id = fields.Char(string="EbayID")
	suffix = fields.Char(string="Suffix")

class ebay_log(models.Model):
	_name = 'ebay.log'

	datetime = fields.Datetime()
	name = fields.Char()
	error = fields.Text()


class ebay_categories_line(models.Model):
	_name = 'ebay.categories.line'

	version_id = fields.Integer()
	categoryID = fields.Integer(readonly=True)
	name = fields.Char()
	level = fields.Integer()
	parent = fields.Integer()

class ebay_template(models.Model):
	_name = 'ebay.template'

	name = fields.Char()
	template_content = fields.Text()


class ebay_message(models.Model):
	_name = 'ebay.message'
	_order = "rcv_date desc"

	name = fields.Char(string="Subject")
	content = fields.Html(string="Content")
	flagged = fields.Boolean(string="Flagged")
	high_priority = fields.Boolean(string="High priority")
	item_id = fields.Char(string="ItemID")
	message_id = fields.Char(string="MessageID")
	external_message_id = fields.Char(string="External Message ID")
	msg_type = fields.Char(string="Type")
	qst_type = fields.Char(string="Question type")
	is_read = fields.Boolean(string="Read")
	rcv_date = fields.Datetime(string="Received date")
	replied = fields.Boolean(string="Replied")
	sender_name = fields.Char(string="Sender")
	sent_to_name = fields.Char(string="Sent to name")
	text = fields.Html(string="Text")
	media = fields.Char(string="Attachment")
	ebay_instance_id = fields.Integer(string="Ebay instance ID")
	reply_content = fields.Text(string="Reply")
	show_reply = fields.Boolean(string="Show reply on site")


	def mark_as_read(self, cr, uid, ids, context=None):
		r = self.browse(cr, uid, ids, context=None)
		message_id = r.message_id
		instance = self.pool.get('ebay').browse(cr,uid, [r.ebay_instance_id], context=None)[0]
		cert = instance.cert_id
		dev = instance.dev_id
		app = instance.app_id
		tok = instance.token_id
		(opts, args) = init_options()

		if _mark_as_read(message_id, opts, cert, dev, app, tok):
			r.is_read=True

		return True

	def delete_message(self, cr, uid, ids, context=None):
		r = self.browse(cr, uid, ids, context=None)
		message_id = r.message_id
		instance = self.pool.get('ebay').browse(cr,uid, [r.ebay_instance_id], context=None)[0]
		cert = instance.cert_id
		dev = instance.dev_id
		app = instance.app_id
		tok = instance.token_id
		(opts, args) = init_options()

		if _delete_message(message_id, opts, cert, dev, app, tok):
			r.unlink()
		return True

	def send_reply(self, cr, uid, ids, context=None):
		r = self.browse(cr, uid, ids, context=None)
		message_id = r.external_message_id
		user_id = r.sender_name
		item_id = r.item_id
		body = r.reply_content
		display_to_public = r.show_reply
		instance = self.pool.get('ebay').browse(cr,uid, [r.ebay_instance_id], context=None)[0]
		cert = instance.cert_id
		dev = instance.dev_id
		app = instance.app_id
		tok = instance.token_id
		(opts, args) = init_options()


		if _send_reply(opts, cert, dev, app, tok, message_id, user_id, item_id, body, display_to_public):
			r.replied = True
			odoo_item_id = self.pool.get('product.template').search(cr, uid, [("ebay_id", "=", item_id)], context=None)

			vals = {
				'sent_to': user_id,
				'item_id': odoo_item_id,
				'backup_item_id': item_id,
				'timestamp': datetime.datetime.now(),
				'body': body
			}
			self.pool.get('ebay.sent.message').create(cr, uid, vals, context=None)

		return True

class ebay_sent_message(models.Model):
	_name = 'ebay.sent.message'

	sent_to = fields.Char(string="Sent to")
	timestamp = fields.Datetime(string="Sent at")
	item_id = fields.Many2one('product.template', string="Product", context="[('ebay_id', '!=', False)]")
	backup_item_id = fields.Char(string="Backup item ID")
	body = fields.Text(string="Message body")

class send_order_message_wizard(models.TransientModel):
	_name = "ebay.order.message"

	def _get_recipient(self):
		so = self.pool.get('sale.order').browse(self._cr, self._uid, self._context.get('active_ids'), context=None)
		return so.partner_id.ebay_id
	def _get_item(self):
		so = self.pool.get('sale.order').browse(self._cr, self._uid, self._context.get('active_ids'), context=None)
		for l in so.order_line:
			if l.product_id.product_tmpl_id.ebay_id:
				return l.product_id.product_tmpl_id.ebay_id

	def _get_instance(self):
		so = self.pool.get('sale.order').browse(self._cr, self._uid, self._context.get('active_ids'), context=None)
		return so.ebay_instance_id

	instance_id = fields.Integer()
	item_id = fields.Char(default=_get_item)
	message = fields.Text()
	copy_to_sender = fields.Boolean()
	question_type = fields.Selection([('CustomizedSubject', 'Customized Subject'), ('General', 'General'), ('MultipleItemShipping', 'Multiple Item Shipping'), ('None', 'None'), ('Payment', 'Payment'), ('Shipping', 'Shipping')])
	recipient_id = fields.Char(default=_get_recipient)
	subject = fields.Char()

	def send_order_message(self, cr, uid, ids, context=None):
		msg = self.browse(cr, uid, ids, context=None)

		if not msg.instance_id:
			raise osv.except_osv(_('Error sending message'), _('Message cannot be sent at the time. SO has no info on instance it was imported from'))
		instance = self.pool.get('ebay').browse(cr, uid, [msg.instance_id], context=None)
		cert = instance.cert_id
		dev = instance.dev_id
		app = instance.app_id
		tok = instance.token_id
		(opts, args) = init_options()

		api = Trading(debug=opts.debug, config_file=None, appid=app, token=tok,
                      certid=cert, devid=dev, warnings=True, timeout=20)

		api.execute('AddMemberMessageAAQToPartner', {'ItemID': msg.item_id, 'MemberMessage':{'Body': msg.message, 'EmailCopyToSender': msg.copy_to_sender, 'QuestionType':msg.question_type, 'RecipientID':msg.recipient_id, 'Subject': msg.subject}})
		rsp = json.loads(api.response.json())
		print rsp
		if rsp["Ack"] == "Failure":
			raise osv.except_osv(_('Error sending message'), _('Message cannot be sent at the time. Ebay failed to send message: %s' % rsp['Errors']['LongMessage']))

		vals = {
				'sent_to': msg.recipient_id,
				'item_id': self.pool.get('product_template').search(cr, uid, [("ebay_id", "=", msg.item_id)], context=None) or None,
				'backup_item_id': msg.item_id,
				'timestamp': datetime.datetime.now(),
				'body': msg.message
		}
		self.pool.get('ebay.sent.message').create(cr, uid, vals, context=None)

		return True
class cancel_request(models.Model):
	_name = "ebay.cancel.request"

	user_id = fields.Char(string="Ebay username")
	order_id = fields.Char(string="Order ID")
	approved = fields.Boolean(string="Approved")
	rejected = fields.Boolean(string="Rejected")

class ebay_shipping_service(models.Model):
	_name = "ebay.shipping.service"

	is_cod = fields.Boolean(string="Service is COD")
	name = fields.Char(string="Description")
	shipping_name = fields.Char(string="TechName")
	international = fields.Boolean(string="International")
	shipping_type = fields.Char(string="Shipping Type")

class order_combine(models.TransientModel):
	_name = "ebay.order.combine"

	def _get_total(self):
		so_ids = self._context.get('active_ids')
		total = 0
		for so in self.pool.get('sale.order').browse(self._cr, self._uid, so_ids, context=None):
			for sol in so.order_line:
				if sol.name != "Delivery cost":
					total += sol.price_subtotal * (1+sol.tax_id.amount or 0.22)
		return total

	def _get_delivery(self):
		so_ids = self._context.get('active_ids')
		total = 0
		for so in self.pool.get('sale.order').browse(self._cr, self._uid, so_ids, context=None):
			for sol in so.order_line:
				if sol.name == "Delivery cost":
					total += sol.price_subtotal * (1+ sol.tax_id.amount or 0.22)
		return total

	def _get_untaxed(self):
		so_ids = self._context.get('active_ids')
		total = 0
		for so in self.pool.get('sale.order').browse(self._cr, self._uid, so_ids, context=None):
			for sol in so.order_line:
				if sol.name != "Delivery cost":
					total += sol.price_subtotal
		return total

	def _get_taxes(self):
		so_ids = self._context.get('active_ids')
		total = 0
		for so in self.pool.get('sale.order').browse(self._cr, self._uid, so_ids, context=None):
			for sol in so.order_line:
				if sol.name != "Delivery cost":
					total += sol.price_subtotal * sol.tax_id.amount or 0.22
		return total

	def _get_items(self):
		so_ids = self._context.get('active_ids')
		total = ''
		for so in self.pool.get('sale.order').browse(self._cr, self._uid, so_ids, context=None):
			for sol in so.order_line:
				if sol.name != "Delivery cost":
					if len(total)>0:
						total += ", "
					total += sol.product_id.name + " (" + str(int(sol.product_uom_qty)) + ")"
		return total
	def _get_customer(self):#also checks SOS
		so_ids = self._context.get('active_ids')
		if len(so_ids)==1:
			raise osv.except_osv(_("ERROR COMBINING ORDERS"), _("Please choose more that one order from same customer to combine"))

		customer = None

		for so in self.pool.get('sale.order').browse(self._cr, self._uid, so_ids, context=None):

			if so.state not in ['draft', 'sent']:
				raise osv.except_osv(_("ERROR COMBINING ORDERS"), _("You can only combined active (not canceled), not paid orders"))

			if customer and customer != so.ebay_username:
				raise osv.except_osv(_("ERROR COMBINING ORDERS"), _("You cannot combine orders from different customers"))

			customer = so.ebay_username
		return customer

	def _get_final_total(self):
		so_ids = self._context.get('active_ids')
		total = 0
		for so in self.pool.get('sale.order').browse(self._cr, self._uid, so_ids, context=None):
			total += so.amount_total
		return total
	def _get_item_count(self):
		so_ids = self._context.get('active_ids')
		total = 0
		for so in self.pool.get('sale.order').browse(self._cr, self._uid, so_ids, context=None):
			for sol in so.order_line:
				if sol.name != "Delivery cost":
					total += int(sol.product_uom_qty)
		return total
	def _get_order_lines(self):
		so_ids = self._context.get('active_ids')
		line_ids = []
		for so in self.pool.get('sale.order').browse(self._cr, self._uid, so_ids, context=None):
			for sol in so.order_line:
				if sol.name != "Delivery cost":
					line_ids.append(sol.id)
		print line_ids
		return line_ids
	def _get_orders(self):
		so_ids = self._context.get('active_ids')
		line_ids = []
		for so in self.pool.get('sale.order').browse(self._cr, self._uid, so_ids, context=None):
			line_ids.append(so.id)

		return line_ids
	def _get_instance_id(self):
		so_ids = self._context.get('active_ids')
		instance_id = False
		for so in self.pool.get('sale.order').browse(self._cr, self._uid, so_ids, context=None):

			if instance_id and instance_id != so.ebay_instance_id:
				raise osv.except_osv(_("ERROR COMBINING ORDERS"), _("Orders you are trying to combine were not imported from same ebay instance"))
			instance_id = so.ebay_instance_id
		return instance_id

	shipping_services = fields.Many2one('ebay.shipping.service', string="Shipping service")
	customer = fields.Char(string="Customer", default=_get_customer)
	items = fields.Text(string="Items", default=_get_items)
	order_lines = fields.One2many('sale.order.line', 'tmp_combine', string="Order lines", default=_get_order_lines)
	orders = fields.One2many('sale.order', 'tmp_combine', string="Orders", default=_get_orders)
	amount_untaxed = fields.Float(string="Items total without taxes", default=_get_untaxed)
	total_taxes = fields.Float(string="Taxes for items", default=_get_taxes)
	total = fields.Float(string="Total cost for items", default=_get_total)
	new_shipping_cost = fields.Float(string="Shipping cost with taxes", default=_get_delivery)
	total_sum = fields.Float(sting="Total amount to pay", default=_get_final_total)
	no_of_items = fields.Float(string="Number of items", default=_get_item_count)
	instance_id = fields.Integer(string="Instance ID", default=_get_instance_id)


	def order_combine(self, cr, uid, ids, context=None):
		sf = self.browse(cr, uid, ids, context=None)
		creating_user_role = "Seller"
		payment_methods = ['PayPal']
		shipping = {"ShippingService": "USPSStandardPost", "ShippingServiceCost": sf.new_shipping_cost, "ShippingServicePriority":1}
		total = sf.total_sum
		items = {"Transaction":[{"Item":{"ItemID": x.ebay_item_id}, "TransactionID": x.transaction_id} for x in sf.order_lines]}
		val = {
			'CreatingUserRole': creating_user_role,
			'PaymentMethods':payment_methods,
			'ShippingDetails': {
				'ShippingServiceOptions':shipping
			},
			'Total':{
				'@attrs': {'currencyID': 'EUR'},
                '#text': total
			},


			'TransactionArray':items
		}
		print val
		instance = self.pool.get('ebay').browse(cr, uid, sf.instance_id, context=None)

		cert = instance.cert_id
		dev = instance.dev_id
		app = instance.app_id
		tok = instance.token_id
		(opts, args) = init_options()

		api = Trading(debug=opts.debug, config_file=None, appid=app, token=tok,
                      certid=cert, devid=dev, warnings=True, timeout=20)
		api.execute('AddOrder', {'Order':val})
		response = json.loads(api.response.json())
		print response
		if "OrderID" not in response or not response["OrderID"]:
			raise osv.except_osv(_("EBAY ORDER COMBINE"), _("Order combination failed!"))
		new_order = json.loads(getOrders(opts, cert, dev, app, tok, response["OrderID"]))
		if _import_order(self, cr, uid, ids, new_order["OrderArray"]["Order"][0], instance):
			oids = [x.id for x in sf.orders]
			print oids
			self.pool.get('sale.order').unlink(cr, uid, oids, context=None)
		else:
			raise osv.except_osv(_("EBAY ORDER COMBINE"), _("Order is combined successfully on ebay but import of newly created order to odoo failed!"))
		return True


def _create_requested_cancel(self, cr, uid, o):
	self.pool.get('ebay.cancel.request').create(cr, uid, {'user_id': o['BuyerUserID'], 'order_id': o["OrderID"]}, context=None)
	return True

#define connection
def init_options():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)

    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="Enabled debugging [default: %default]")
    parser.add_option("-y", "--yaml",
                      dest="yaml", default='/home/gigra/ebay.yaml',
                      help="Specifies the name of the YAML defaults file. [default: %default]")
    parser.add_option("-a", "--appid",
                      dest="appid", default=None,
                      help="Specifies the eBay application id to use.")
    parser.add_option("-p", "--devid",
                      dest="devid", default=None,
                      help="Specifies the eBay developer id to use.")
    parser.add_option("-c", "--certid",
                      dest="certid", default=None,
                      help="Specifies the eBay cert id to use.")
    parser.add_option("-m", "--domain", dest="domain", default="api.sandbox.ebay.com", help="Specifies domain of app")

    (opts, args) = parser.parse_args()
    return opts, args

def getCategories(opts, cert, dev, app, tok):

    try:
        api = Trading(debug=opts.debug, config_file=None, appid=app, token=tok,
                      certid=cert, devid=dev, warnings=True, timeout=20)

        api.execute('GetCategories', {'CategorySiteID': 101, 'CategoryParent': 58058, 'ViewAllNodes': False, 'DetailLevel': 'ReturnAll'}) #101 = Italy

        categories = json.loads(api.response.json())

    except ConnectionError as e:
        #log error e.response
        return False

    return categories

def save_product(pro,  name, desc, lst_up, defs):
		_logger = logging.getLogger(__name__)

		cert = defs.cert_id
		dev = defs.dev_id
		app = defs.app_id
		tok = defs.token_id

		_logger.info("---- %s, %s, %s, %s" % (cert, dev, app, tok))

		(opts, args) = init_options()
		qty = 0

		if pro.qty_available > 0:
			qty = pro.qty_available
		else:
			_logger.warning("***NO Stock***")
			return {'Error':"INSUFFICIENT STOCK"}

		if not pro.stock_limit or defs.override_default:
			stock_limit = defs.ebay_stock_limit
		else:
			stock_limit = pro.stock_limit

		if qty > stock_limit:
			qty = stock_limit

		qty = int(qty)

		ean = "N/A"
		if pro.ean13:
			ean = pro.ean13



		cps = "N/A"
		if pro.copies or pro.no_of_copies:
			cps = pro.copies or pro.no_of_copies

		cat_id = pro.categ_id.ebay_category_id.categoryID
		if not cat_id:
			_logger.warning("***NO CATEGORY***")
			return {'Error': "EBAY CATEGORY NOT SPECIFIED"}

		cd = name

		desc = desc

		if not desc:
			_logger.warning("***NO TITLE***")
			return {'Error':"ITEM HAS NO TITLE"}


		image_url = uploadPictureFromFilesystem(opts,cert, app, dev, tok, pro.name, pro.image)
		if not image_url:
			_logger.warning("***NO IMG**")
			return {'Error':"FAILED TO UPLOAD IMAGE"}

		if pro.ebay_template_id:
			template = pro.ebay_template_id.template_content
		if not pro.ebay_template_id or defs.override_default:
			template = defs.ebay_template_id.template_content

		#parse template
		if template:
			tmp = '<![CDATA['
			tmp += template
			tmp = tmp.replace('[#title#]', desc)
			tmp = tmp.replace('[#url_image1#]', image_url)
			tmp = tmp.replace('[#description#]', pro.description)
			tmp = tmp.replace('[#extra1#]', pro.ebay_custom_desc or '')
			tmp = tmp.replace('[#sku#]', cd)
			tmp = tmp.replace('[#code#]', pro.name)
			tmp = tmp.replace('[#OEM#]', pro.oem_code)
			tmp = tmp.replace('[#no_copy#]', str(cps))
			tmp = tmp.replace('[#EAN13#]', ean)
			#tmp = tmp.replace('[#menu#]', cat_html)
			tmp = tmp + ']]>'




		ebay_price = pro.ebay_price
		if not ebay_price or defs.override_default:
			ebay_price = float(pro.list_price) - float(defs.ebay_price_formula)


		shipping_c = pro.ebay_shipping_cost
		if not shipping_c or defs.override_default:
			shipping_c = defs.ebay_shipping_cost

		add_shipping_c = pro.ebay_additional_item_cost
		if not add_shipping_c or defs.override_default:
			add_shipping_c = defs.ebay_shipping_additional

		list_dur = pro.ebay_listing_duration
		if not list_dur or defs.override_default:
			list_dur = defs.ebay_listing_dur


		post_code = pro.ebay_item_location
		if not post_code or defs.override_default:
			post_code = defs.ebay_item_loc

		paypal = defs.ebay_paypal_email

		myitem = {
			"Item": {
				"Title": desc,
				"Description": tmp,
				"PrimaryCategory": {"CategoryID": pro.categ_id.ebay_category_id.categoryID}, #FROM CATEGORY BOUND WITH ITEM
				"StartPrice": ebay_price,
				"CategoryMappingAllowed": "true",
				"Country": "IT",
				"ConditionID": "1000",
				"ListingDuration": list_dur,
				"InventoryTrackingMethod": "SKU",
				"Currency": "EUR",
				"DispatchTimeMax": "5",
				"ListingType": "FixedPriceItem",
				"PaymentMethods": ["CashOnPickup", "PayPal"],
				"PayPalEmailAddress": paypal,
				"PictureDetails": {"PictureURL":image_url}, #"PictureSource": p.image
				"Quantity": qty,
				"PostalCode": post_code,
				"ProductListingDetails":{
					"EAN": ean
				},
				"ReturnPolicy": {
					"EAN": ean,
					"ReturnsAcceptedOption": "ReturnsAccepted",
					"RefundOption": "MoneyBack",
					"ReturnsWithinOption": "Days_14",
					"Description": "If you are not satisfied, return the product",
					"ShippingCostPaidByOption": "Buyer"
				},
				"SKU": cd,
				"ShippingDetails": {
					"ShippingType":"Flat",
					"ShippingServiceOptions": {
						"FreeShipping": pro.ebay_free_shipping,
						"ShippingService": "IT_ExpressCourier",
						"ShippingServiceCost":  shipping_c,
						"ShippingServiceAdditionalCost": add_shipping_c

					}


				},
				"ItemSpecifics": {
					"NameValueList": [{
						"Name": "EAN",
						"Value": ean
					}, {
						"Name": "Brand",
						"Value": 'Senza Marca/Generico'
					},{
						"Name": "MPN",
						"Value": 'Non applicabile'
					},{
						"Name": "IBAN",
						"Value": 'Non applicabile'
					}]
				},
				"VATDetails": {
					"VATPercent": "22"
					},
				"Site": "Italy"
			}
		}

		return myitem

def completeSale(opts, cert, dev, app, tok, data):
	try:
		api = Trading( debug=opts.debug, config_file=None, appid=app,
					certid=cert, devid=dev,token=tok, warnings=False, siteid=101)
		api.execute('CompleteSale', data)
		resp = json.loads(api.response.json())
		return resp['Ack']
	except ConnectionError as e:
		error = json.loads(e.response.json())

		_logger.warning("*****ERROR: %s" % error)

def addItem(i, myitem, ebay_id=None):
	_logger = logging.getLogger(__name__)
	cert = i.cert_id
	dev = i.dev_id
	app = i.app_id
	tok = i.token_id
	(opts, args) = init_options()

	#DEBUG - DEBUG - DEBUG
	with open('/opt/odoo/gigra_addons/ebay_connector/item.txt', 'w') as outfile:
		json.dump(myitem, outfile)
	try:
		api = Trading( debug=opts.debug, config_file=None, appid=app,
					certid=cert, devid=dev,token=tok, warnings=False, siteid=101)

		if ebay_id:
			_logger.info("GOING TO REVISE %s" % ebay_id)
			api.execute('ReviseFixedPriceItem', myitem)
			resp = json.loads(api.response.json())
			_logger.info("RESPONSE REVISE: %s" % resp)
			return 1, resp
		else:
			_logger.info("GOING TO INSERT NEW %s" % ebay_id)
			api.execute('AddFixedPriceItem', myitem)

		resp = json.loads(api.response.json())
		ebay_id = None
		ebay_date = None
		ebay_id = resp["ItemID"]
		ebay_date = datetime.datetime.now()
		return ebay_id, ebay_date

	except ConnectionError as e:
		error = json.loads(e.response.json())
		#eCode = error["Errors"]["ErrorCode"]
		_logger.warning("*****ERROR: %s" % error)
		return None, error

def removeFromEbay(opts, cert, dev, app, tok, ebay_ids):
	_logger = logging.getLogger(__name__)
	try:
		api = Trading( debug=opts.debug, config_file=None, appid=app,
					certid=cert, devid=dev,token=tok, warnings=False, siteid=101)
		res = {}
		for eid in ebay_ids:
			api.execute('EndFixedPriceItem', {'EndingReason': 'NotAvailable', 'ItemID': eid})
			resp = json.loads(api.response.json())
			res[eid] = resp['Ack']

		return res
	except ConnectionError as e:
		error = json.loads(e.response.json())
		#eCode = error["Errors"]["ErrorCode"]
		_logger.warning("*****ERROR: %s" % error)
		return False

def uploadPictureFromFilesystem(opts,cert, app, dev, tok, code, image):
	api = Trading( debug=opts.debug, config_file=None, appid=app,
				  certid=cert, devid=dev,token=tok, warnings=True, timeout=300)

	_logger = logging.getLogger(__name__)

	filepath = '/opt/odoo/ebay_temp/%s.jpg' % code

	_logger.info("Filepath %s" % filepath)
	try:
		img = open(filepath, 'rb')
	except:
		_logger.info("CANT OPEN")
		img = image
		return False
	files = {'file': ('EbayImage', img)}

	pictureData = {
		"WarningLevel": "High",
		"PictureName": code
	}

	api.execute('UploadSiteHostedPictures', pictureData, files=files)

	response = json.loads(api.response.json())
	return response["SiteHostedPictureDetails"]["FullURL"]

"""
def manual_auth(username, hostname, t):
	path = "/opt/odoo/gigra_addons/ebay_connector/id_dsa"
	try:
		key = paramiko.RSAKey.from_private_key_file(path)
	except paramiko.PasswordRequiredException:
		password = 'seSea127'
		key = paramiko.RSAKey.from_private_key_file(path, password)
	t.auth_publickey(username, key)

def getImage(code):
	username = 'sea'

	hostname = 'sea.z-web.it'

	port = 22

	try:
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.connect((hostname, port))
	except Exception as e:
		print('*** Connect failed: ' + str(e))


	t = paramiko.Transport(sock)

	try:
		t.start_client()
	except paramiko.SSHException:
		print('*** SSH negotiation failed.')

	try:
		keys = paramiko.util.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
	except IOError:
		try:
			keys = paramiko.util.load_host_keys(os.path.expanduser('~/ssh/known_hosts'))
		except IOError:
			print('*** Unable to open host keys file')
			keys = {}


	key = t.get_remote_server_key()
	if hostname not in keys:
		print('*** WARNING: Unknown host key!')
	elif key.get_name() not in keys[hostname]:
		print('*** WARNING: Unknown host key!')
	elif keys[hostname][key.get_name()] != key:
		print('*** WARNING: Host key has changed!!!')



	manual_auth(username, hostname, t)


	filepath = '/img/%s.jpg' % code
	localpath = '/opt/odoo/ebay_temp/%s.jpg' % code001H1010VC
	sftp = paramiko.SFTPClient.from_transport(t)
	sftp.get(filepath, localpath)

	return True
"""
def getOrders(opts, cert, dev, app, tok, order_id=None):
	_logger = logging.getLogger(__name__)
	try:
		api = Trading( debug=opts.debug, config_file=None, appid=app,
                      certid=cert, devid=dev,token=tok, warnings=True, timeout=300)

		if order_id:
			print order_id
			api.execute('GetOrders', {'OrderIDArray': {'OrderID':order_id}})
        	#api.execute('GetOrderTransactions', {'OrderIDArray': {'OrderID':order_id}})
		else:
			api.execute('GetOrders', {'NumberOfDays': 2, 'OrderStatus': 'All',  'DetailLevel': 'ReturnAll'})
        #api.execute('GetOrderTransactions', {'OrderIDArray': {'OrderID':'131201365591-1190809310003'}})
		res = api.response.json()
		res = json.loads(res)
		orders = res["OrderArray"]["Order"]
		total_pages = res['PaginationResult']['TotalNumberOfPages']
		total_entries = res['PaginationResult']['TotalNumberOfEntries']
		total_pages = int(total_pages)
		_logger.info('---- TOTALS: %s %s' % (total_pages, total_entries))
		if total_pages > 1:
			for i in range(2,total_pages+1):
				api.execute('GetOrders', {'NumberOfDays': 2, 'OrderStatus': 'All',  'Pagination': {'PageNumber': i, 'EntriesPerPage': 100}, 'DetailLevel': 'ReturnAll'})
				new_res = api.response.json()
				new_res = json.loads(new_res)
				for x in new_res["OrderArray"]["Order"]:
					orders.append(x)

		return orders

	except ConnectionError as e:
		print(e)

def logError(cr, uid, name, error, context):
	log_tmp = self.pool.get('ebay.log')
	val = {
		'name': name,
		'error': error,
		'date': datetime.datetime.now()

	}
	log_tmp.create(cr, uid, val, context=context)

	return True

def _get_messages_hdr(opts, cert, dev, app, tok):
	api = Trading(debug=opts.debug, config_file=None, appid=app,
                      certid=cert, devid=dev,token=tok, warnings=True, timeout=300)

	api.execute('GetMyMessages', {'DetailLevel': 'ReturnHeaders'})
	print api.response.reply
	return json.loads(api.response.json())

def _get_messages(opts, cert, dev, app, tok, to_get):
	api = Trading(debug=opts.debug, config_file=None, appid=app,
                      certid=cert, devid=dev,token=tok, warnings=True, timeout=300)
	responses = []
	counter = 0
	for tg in to_get:
		print tg["MessageID"]
		api.execute('GetMyMessages', {'DetailLevel': 'ReturnMessages', 'MessageIDs':{'MessageID':tg['MessageID']}, 'OutputSelector': 'Text'})
		try:
			content = api.response.reply.Messages.Message.Text
			responses.append({'header': tg, 'content': content})
		except:
			responses.append({'header': tg, 'content': 'Message has no content'})


	return responses

def _mark_as_read(message_id, opts, cert, dev, app, tok):
	api = Trading(debug=opts.debug, config_file=None, appid=app,
                      certid=cert, devid=dev,token=tok, warnings=True, timeout=300)

	api.execute('ReviseMyMessages', {'MessageIDs':{'MessageID': message_id}, 'Read': True})

	if json.loads(api.response.json())["Ack"] == "Success":
		return True
	else:
		return False

def _delete_message(message_id, opts, cert, dev, app, tok):
	api = Trading(debug=opts.debug, config_file=None, appid=app,
                      certid=cert, devid=dev,token=tok, warnings=True, timeout=300)

	api.execute('DeleteMyMessages', {'MessageIDs':{'MessageID': message_id}})

	if json.loads(api.response.json())["Ack"] == "Success":
		return True
	else:
		return False

def _send_reply(opts, cert, dev, app, tok, message_id, user_id, item_id, body, display_to_public):
	api = Trading(debug=opts.debug, config_file=None, appid=app,
                      certid=cert, devid=dev,token=tok, warnings=True, timeout=300)

	print {'ItemID':item_id, 'MemberMessage':{'Body': body, 'DisplayToPublic': display_to_public, 'ParentMessageID': message_id, 'RecipientID': user_id}}
	api.execute('AddMemberMessageRTQ', {'ItemID':item_id, 'MemberMessage':{'Body': body, 'DisplayToPublic': display_to_public, 'ParentMessageID': message_id, 'RecipientID': user_id}})

	if json.loads(api.response.json())['Ack'] == "Success":
		return True
	else:
		return False

def _create_cron(self, cr, uid, name, tech_name, function, interval, interval_type):
		cr_vals = {
			'active': True,
			'display_name': name,
			'function': function,
			'interval_number': interval,
			'interval_type': interval_type,
			'model': 'ebay',
			'name': tech_name,
			'numbercall': -1,
			'priority': 1
		}
		return self.pool.get('ir.cron').create(cr, uid, cr_vals, context=None)

def _get_services(opts, cert, dev, app, tok):
	api = Trading(debug=opts.debug, config_file=None, appid=app,
                      certid=cert, devid=dev,token=tok, warnings=True, timeout=300)

	api.execute('GeteBayDetails', {'DetailName': 'ShippingServiceDetails'})
	response = json.loads(api.response.json())

	if response['Ack'] == "Success":

		res = []
		for s in response['ShippingServiceDetails']:
			print s
			vals = {
				'name': s['Description'],
				'shipping_name': s['ShippingService'],
				'shipping_type': s['ServiceType'] if 'ServiceType' in s else None,
				'is_cod':s['CODService'] if 'CODService' in s else None,
				'international': s['InternationalService'] if 'InternationalService' in s else None
			}
			res.append(vals)
		return res
	else:
		return False



def _import_order(self, cr, uid, ids, o, r, context=None):
			_logger = logging.getLogger(__name__)
			r = r[0]
			_logger.info("____ %s " % o)
			res_par = self.pool.get('res.partner')

			pro_tmp = self.pool.get('product.template')
			#SELECT WHICH IS THE CASE
			#NOT PAID, CANCELED
			extra_note = ''
			if o["OrderStatus"] == "Active" and o["CheckoutStatus"]["Status"] == "Incomplete" and "PaidTime" not in o:
				paid = False
				delivered = False
				print "NOT PAID, CANCELED"
				print o["OrderID"], o['BuyerUserID']
			#PAID
			elif o["OrderStatus"] == "Completed" and o['CheckoutStatus']['Status'] == "Complete" and "PaidTime" in o:
				paid = True
				delivered = False
				print "PAID"
				print o["OrderID"], o['BuyerUserID']
			#PAID AND DELIVERED
			elif o["OrderStatus"] == "Completed" and o['CheckoutStatus']['Status'] == "Complete" and "PaidTime" in o and "ShippedTime" in o:
				paid = True
				delivered = True
				print "PAID AND DELIVERED"
				print o["OrderID"], o['BuyerUserID']
			else:
				paid = False
				delivered = False
				print "DOES NOT BELONG ANYWHERE"
				print o["OrderID"], o['BuyerUserID']
				extra_note = "****ODOO IMPORT MESSAGE**** THIS ONE DOES NOT BELONG ANYWHERE"
				#return False


			#check if exists
			xid = self.pool.get('sale.order').search(cr, uid, [('ebay_id', '=', o["OrderID"])], context=context)
			if xid:
				this_so = self.pool.get('sale.order').browse(cr, uid, xid, context=None)

			user_id = r.default_user.id if r.default_user else uid
			eb_order_id = o['OrderID']
			ebay_date = o['CreatedTime']
			ebay_paid_date = o["PaidTime"] if paid else None
			ebay_delivered_date = o["ShippedTime"] if delivered else None

			#SOL data
			sols = []

			ebay_pricelist = r.ebay_pricelist_id
			if not ebay_pricelist:
				raise osv.except_osv(_('Error importing orders'), _('Default pricelist is not set! \nGo on instance configuration and set Default Pricelist'))

			ebay_pay_term = r.ebay_payment_term_id
			if not ebay_pay_term:
				raise osv.except_osv(_('Error importing orders'), _('Default payment term is not defined! \nGo on instance configuration and set Default Payment Term'))
			#define partner
			#get username (unique identifier)
			uname = o['BuyerUserID']
			_logger.info("---- IMPORTING ORDER %s (%s)" % (o['BuyerUserID'], float(o["Total"]["value"])))
			#namex = o['ShippingAddress']['Name'] if 'ShippingAddress' in o else ''
			p_ids = res_par.search(cr, uid, [("ebay_id", "=", uname)], context=context)
			#if not p_ids:
			#	p_ids = res_par.search(cr, uid, [("name", "=", namex)], context=context)

			if p_ids:
				partner_id = res_par.browse(cr, uid, p_ids, context=context)[0].id
				shipping_partner_id = res_par.search(cr, uid, [('parent_id', '=', partner_id), ('type', '=', 'delivery')], context=None)
				if shipping_partner_id:
					shipping_partner_id = shipping_partner_id[0]
			else:

				shipping_address = o['ShippingAddress']
				name = shipping_address['Name'] if shipping_address['Name'] else uname
				province = shipping_address['StateOrProvince']
				province_id = None
				if province:
					prov_ids = self.pool.get('res.country.state').search(cr, uid, [('code', '=', province), ('country_id', '!=', 235)], context=None)
					if prov_ids:
						province_id = prov_ids[0]



				comment = "Ebay addressID: %s" % shipping_address['AddressID'] if 'AddressID' in shipping_address else 'not defined'
				street = shipping_address['Street1'] if 'Street1' in shipping_address else None
				if 'Street2' in shipping_address and shipping_address['Street2']:
					street += ", %s" % shipping_address['Street2']
				city = shipping_address["CityName"] if "CityName" in shipping_address else ''
				ebay_country = shipping_address['Country'] if "Country" in shipping_address else ''
				lang = ebay_country.lower() + "_" + ebay_country
				if lang not in ['en_US', 'it_IT', 'de_DE', 'fr_FR']:
					lang = "it_IT"
				country_id = self.pool.get('res.country').search(cr, uid, [("code", "=", ebay_country)], context=None)
				if country_id:
					country_id = country_id[0]
				else:
					comment += ", COUNTRY: %s" % shipping_address['CountryName'] if 'CountryName' in shipping_address else "not defined"
				phone = shipping_address['Phone'] if "Phone" in shipping_address else None
				zip_code = shipping_address['PostalCode'] if "PostalCode" in shipping_address else None

				ebay_id = uname
				new_part = {
					'name': name,
					'comment': comment,
					'street': street,
					'city': city,
					'country_id': country_id,
					'phone': phone,
					'zip': zip_code,

					'state_id': province_id,
					'is_company': True,
					'ebay_id': ebay_id,
					'property_product_pricelist': ebay_pricelist.id,
					'property_payment_term': ebay_pay_term.id,
					'lang': lang,
					'goods_description_id': r.ebay_goods_description.id if r.ebay_goods_description else None,
					'carriage_condition_id': r.ebay_carriage_condition.id if r.ebay_carriage_condition else None,
					'transportation_reason_id': r.ebay_transportation_reason.id if r.ebay_transportation_reason else None,
					'transportation_method_id': r.ebay_transportation_method.id if r.ebay_transportation_method else None,
					'property_account_position': r.ebay_account_position.id if r.ebay_account_position else None,
					'category_id': [[4,1]]
				}
				#print new_part
				#email = is problematic


				partner_id = res_par.create(cr, uid, new_part, context=context)
				if partner_id:
					sh_part_vals = {
						'type': 'delivery',
						'parent_id': partner_id,
						'name': name,
						'street': street,
						'city': city,
						'country_id': country_id,
						'phone': phone,
						'zip': zip_code,
						'state_id': province_id,
					}
					try:
						shipping_partner_id = res_par.create(cr, uid, sh_part_vals, context=context)
					except:
						shipping_partner_id = 0

			if not partner_id:
				raise osv.except_osv(_('Error importing orders'), _('Error creating or finding client %s on odoo' % new_part['name']))

			partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=None)

			amount_total = float(o["Total"]["value"])

			pricelist_id = self.pool.get('product.pricelist').search(cr, uid, [("name", "=", 'EBAY')], context=None)
			if pricelist_id:
				pricelist_id = pricelist_id[0]
			else:
				pricelist_id = 1

			payment_method = o['CheckoutStatus']['PaymentMethod'] if 'PaymentMethod' in o['CheckoutStatus'] else None
			pm_id = 4
			if payment_method:
				pm_ids = self.pool.get('payment.method').search(cr, uid, [('name', '=', payment_method)], context=None)
				if pm_ids:
					pm_id = pm_ids[0]
			for ol in o["TransactionArray"]["Transaction"]:

				buyer_email = ol['Buyer']['Email'] if 'Email' in ol['Buyer'] else None
				if buyer_email and buyer_email != partner.email:
					partner.email = buyer_email

				pro_name = ol["Item"]["SKU"]
				pro_name = pro_name.split("_")[0]
				#_logger.info("************ %s" % pro_name)

				pro_ids = self.pool.get('product.product').search(cr, uid, [("product_tmpl_id.name", "=", pro_name)], context=context)

				if pro_ids:
					pro_id =  pro_ids[0]
					product = self.pool.get('product.product').browse(cr, uid, pro_id, context=None)
					pro_desc = product.description
					if not pro_desc:
						pro_desc = "-"
					if product:
						tmp_id = product.product_tmpl_id.id
						#_logger.info("********* TMP ID: %s" % tmp_id)
				else:
					#log
					vals = {
						'name': pro_name,
						'categ_id': r.default_categ.id or 1,
						'description': "***** Product created on EBAY import, please fill in missing data ****"
					}
					pro_desc = '-'
					new_prod = self.pool.get('product.template').create(cr, uid, vals, context=None)
					tmp_id = new_prod
					pro_id = self.pool.get('product.product').search(cr, uid, [('product_tmpl_id.id', '=', tmp_id)], context=None)
					if not pro_id:
						raise osv.except_osv(_('Error importing orders'), _('There is not product %s on odoo' % pro_name))
					pro_id = pro_id[0]


				untaxed_price = (float(ol["TransactionPrice"]["value"]) / 122) *100
				line = {

					"name": pro_desc,
					"product_uom": 1,
					"product_uos_qty": ol["QuantityPurchased"],
					"price_unit": untaxed_price,
					"product_uom_qty": float(ol["QuantityPurchased"]),
					"order_partner_id": partner_id,
					"order_id": 0,
					"product_id": pro_id,
					"product_tmpl_id": tmp_id,
					"delay": 0,
					"transaction_id": ol["TransactionID"],
					"order_line_item_id": ol["OrderLineItemID"],
					"salesman_id": uid,
					#"pricelist_id": pricelist_id,
					'tax_id': [[4,1]],
					'ebay_item_id': ol['Item']['ItemID']

				}
				sols.append(line)
			if 'ShippingServiceCost' in o['ShippingServiceSelected']:
				untaxed_shipping = (float(o['ShippingServiceSelected']['ShippingServiceCost']['value']) / 122) * 100
				if o['ShippingServiceSelected']['ShippingServiceCost']['value']:
					delivery = {
						"name": "Delivery cost",
						#"description": pro_desc,
						"product_uom": 1,
						"product_uos_qty": 1,
						"price_unit": untaxed_shipping,
						"product_uom_qty": 1,
						"order_partner_id": partner_id,
						"order_id": 0,
						"product_id": [x for x in self.pool.get('product.product').search(cr, uid, [("name", '=', 'Delivery cost')], context=None)][0],
						"product_tmpl_id": [t.product_tmpl_id.id for t in self.pool.get('product.product').browse(cr, uid, self.pool.get('product.product').search(cr, uid, [("name", '=', 'Delivery cost')], context=None), context=None)][0] ,
						"delay": 0,
						#"state": state,
						"salesman_id": uid,
						"pricelist_id": pricelist_id,
						'tax_id': [[4,1]]
					}
					sols.append(delivery)


			order = self.pool.get('sale.order')
			note = o['BuyerCheckoutMessage'] if 'BuyerCheckoutMessage' in o else ''
			note = note + ", %s" % extra_note
			vals = {
				'partner_id': partner_id,

				'pricelist_id': pricelist_id,

				'partner_invoice_id': partner_id,
				'partner_shipping_id': shipping_partner_id or partner_id,
				'order_policy': 'manual',
				'picking_policy': 'direct',
				'warehouse_id': 1,
				'create_uid': user_id,
				'user_id': user_id,
				'company_id': self.pool.get('res.company').search(cr, uid, [], context=None)[0],
				'ebay_id': eb_order_id,
				'ebay_date': ebay_date,
				'ebay_paid_date': ebay_paid_date,
				'ebay_delivered_date': ebay_delivered_date,
				'tax_receipt': True,
				'order_policy':'picking',
				'ebay_username': uname,
				'payment_method_id': pm_id,
				'note': note,
				'ebay_instance_id': r.id
			}

			if xid:
				print "UPDATED %s" % xid
				return {'order':xid[0], 'paid': paid, 'delivered': delivered}


			order_id = order.create(cr, uid, vals, context)
			#order = self.pool.get('sale.order').browse(cr, uid, order_id, context=None)[0]
			#pg = self.pool.get('procurement.group').create(cr, uid, {'name': order.name}, context=None)
			#self.pool.get('sale.order').write(cr, uid, order_id, {'procurement_group_id':pg}, context=None)
			#print {'order':order_id, 'paid': paid, 'delivered': delivered}

			#print {'order':order_id, 'paid': paid, 'delivered': delivered}



			#print "ORDER CREATED WITH ID: " + str(order_id)
			if order_id:
				for x in sols:
					x['order_id'] = order_id

					order_line = self.pool.get('sale.order.line')

					order_line.create(cr, uid, x, context)

			return {'order':order_id, 'paid': paid, 'delivered': delivered}

class AccountInvoice(models.Model):
	_inherit = "account.invoice"
	tracking_sent_to_ebay = fields.Boolean(string="Tracking sent to ebay")
	def complete_sale_ebay(self, cr, uid, ids, context):
		res = self.pool.get('ebay').complete_sale(cr, uid, ids, context=None)
class AccountInvoiceLine(models.Model):
	_inherit = "account.invoice.line"

	ebay_transaction_id = fields.Char(string="Ebay transaction ID")
	ebay_order_id = fields.Char(string="Ebay Order ID")
	ebay_item_id = fields.Char(string="Ebay Item ID")
class ProcurementOrder(models.Model):
	_inherit = "procurement.order"

	ebay_transaction_id = fields.Char(string="Ebay transaction ID")
	ebay_order_id = fields.Char(string="Ebay Order ID")
	ebay_item_id = fields.Char(string="Ebay Item ID")

	def _run_move_create(self, cr, uid, procurement, context=None):
		res = super(ProcurementOrder, self)._run_move_create(cr, uid, procurement, context=context)
		res.update({
			'ebay_transaction_id': procurement.ebay_transaction_id,
			'ebay_order_id': procurement.ebay_order_id,
			'ebay_item_id': procurement.ebay_item_id
		})

		return res
class StockMove(models.Model):
	_inherit = "stock.move"
	ebay_transaction_id = fields.Char(string="Ebay transaction ID")
	ebay_order_id = fields.Char(string="Ebay Order ID")
	ebay_item_id = fields.Char(string="Ebay Item ID")
	def _get_invoice_line_vals(self, cr, uid, move, partner, inv_type, context=None):

		res = super(StockMove, self)._get_invoice_line_vals(cr, uid, move, partner, inv_type)

		res.update({
				'ebay_transaction_id': move.ebay_transaction_id,
				'ebay_order_id': move.ebay_order_id,
				'ebay_item_id': move.ebay_item_id
			})

		return res

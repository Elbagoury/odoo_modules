from openerp import models, fields, api, _
from openerp.osv import osv
import openerp.addons.decimal_precision as dp
from datetime import datetime, timedelta
import logging
import copy

class account_invoice(models.Model):
	_inherit = "account.invoice.line"

	full_subtotal = fields.Float(string="Full subtotal")
	with_discount = fields.Float(string="With discount")
	discount_global = fields.Float(string="Global discount")
	product_price = fields.Float(string="Full price")
	pricelist_discount = fields.Float(string="Pricelist discount (%)")
	custom_note = fields.Char(string="Custom note")

	@api.one
	@api.depends('price_unit', 'discount', 'discount_global', 'invoice_id.discount_method', 'invoice_id.invoice_discount', 'invoice_line_tax_id', 'quantity',
		'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id')
	def _compute_price(self):
		#start = datetime.now()
		if not self.price_unit or not self.quantity:
			return True


		if self.invoice_id:
			if self.invoice_id.discount_method == 'percent':
				self.discount_global = self.invoice_id.invoice_discount
			elif self.invoice_id.discount_method == 'fixed':
				untx = 0
				for line in self.invoice_id.invoice_line:
					untx += line.price_unit * line.quantity
				self.discount_global = self.invoice_id.invoice_discount * 100 / untx
			else:
				self.discount_global = 0.0
		price_with_global = self.price_unit * (1 - (self.discount_global or 0.0) / 100.00)
		price = price_with_global * (1 - (self.discount or 0.0) / 100.0)
		self.with_discount = price_with_global
		self.full_subtotal = self.price_unit * self.quantity
		taxes = self.invoice_line_tax_id.compute_all(price, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
		self.price_subtotal = taxes['total']
		if self.invoice_id:
			self.price_subtotal = self.invoice_id.currency_id.round(self.price_subtotal)

		if self.pricelist_discount:
			#print "HAS PRICELIST_DISCOUNT %s" % self.pricelist_discount
			tp = self.product_price * (1-self.pricelist_discount/100)
			#print tp

			df = tp-self.price_unit
			if df < 0:
				df *= -1
			#print df
			if df > 0 and df > 0.01:
				#print "Changed"
				self.product_price = self.price_unit
				self.pricelist_discount = 0.0
				#print "FINAL VALUES %s %s" % (self.product_price, self.pricelist_discount)
			else:
				#print "Not changed"
		else:
			#print "NOT CHANGED"
			#print self.price_unit
			self.product_price = self.price_unit




class account_invoice(models.Model):
	_inherit = "account.invoice"

	discount_method = fields.Selection([('fixed','Fixed'), ('percent','Percent')], string="Discount method")
	invoice_discount = fields.Float(string="Invoice discount")
	amount_discount = fields.Float(string="Discount", digits=dp.get_precision('Account'),
		store=True, readonly=True, compute='_compute_amount', track_visibility='always')
	discounted = fields.Float(string="Disounted", digits=dp.get_precision("Account"),
		strore=True, readonly=True, compute="_compute_amount", track_visibility="always")

	def confirm_custom(self, cr, uid, ids, context=None):
		return True


	@api.one
	@api.depends('invoice_line.price_subtotal', 'tax_line.amount','invoice_line.discount_global', 'invoice_discount', 'discount_method', 'amount_discount')
	def _compute_amount(self):

		_logger = logging.getLogger(__name__)

		self.amount_untaxed = self.currency_id.round(sum(line.full_subtotal or 0 for line in self.invoice_line))
		self.discounted = sum(line.price_subtotal for line in self.invoice_line)

		self.amount_discount = self.amount_untaxed - self.discounted

		global_disc = 0.0
		lns = [{'product_price': l.product_price, 'pricelist_discount': l.pricelist_discount, 'id': l.id, 'discount_global': l.discount_global} for l in self.invoice_line]

		lines = copy.deepcopy(lns)

		cr = self._cr
		uid = self._uid
		invoice_line_obj = self.pool.get('account.invoice.line')
		line_ids = []

		for l in lines:
			line_ids.append(l['id'])
			global_disc =  l['discount_global']



		global_disc /= 100


		self.amount_tax = sum(line.amount * (1-global_disc) for line in self.tax_line)
		self.amount_total = self.discounted + self.amount_tax


	def create(self, cr, uid, vals, context=None):

		vals['shipping_date'] = datetime.now()

		return super(account_invoice, self).create(cr, uid, vals, context=None)

	@api.multi
	def onchange_partner_id(self, type, partner_id, date_invoice=False,
            payment_term=False, partner_bank_id=False, company_id=False):

		inv = super(account_invoice, self).onchange_partner_id(type, partner_id, date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False)

		####

		if partner_id:
			#print "Has partner ID"
			partner = self.pool.get('res.partner').browse(self._cr, self._uid, partner_id, context=None)
			bank_id = partner.bank_ids and partner.bank_ids[0].id or False
			#print "HAS BANK %s" % bank_id
			if bank_id:
				inv.update({
						'value':{
							'partner_bank_id': bank_id
						}
					})

		return inv

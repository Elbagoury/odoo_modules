from openerp import fields, models, api, _
import openerp.addons.decimal_precision as dp


class sale_order(models.Model):
	_inherit = "sale.order"

	discount_method = fields.Selection([('fixed', 'Fixed'), ('percent', 'Percent')], string="Discount method")
	discount = fields.Float(string="Discount")
	amount_discount = fields.Float(string="Discount amount")

	@api.onchange('discount')
	def onchange_discount(self):
		print "here"
		cr = self._cr
		uid = self._uid
		ids = self._ids
		order = self.browse(ids)[0]
		for ol in order.order_line:
			print ol.price_subtotal


class sale_order_line(models.Model):
	_inherit = "sale.order.line"

	discount_global = fields.Float(string="Global dicount")
	price_subtotal = fields.Function(_amount_line, string="Subtotal", digits_compute=dp.get_precision('Account'))

	def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
		print "Computing amount"
		tax_obj = self.pool.get('account.tax')
		cur_obj = self.pool.get('res.currency')
		res = {}
		if context is None:
			context = {}
		for line in self.browse(cr, uid, ids, context=context):
			price = self._calc_line_base_price(cr, uid, line, context=context)
			qty = self._calc_line_quantity(cr, uid, line, context=context)
			taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, qty,
										line.product_id,
 										line.order_id.partner_id)
			cur = line.order_id.pricelist_id.currency_id
			res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])


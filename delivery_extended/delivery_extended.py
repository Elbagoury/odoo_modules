from openerp.osv import fields, osv
from openerp.tools.translate import _
import time
import openerp.addons.decimal_precision as dp

class res_partner(osv.osv):
	_inherit = 'res.partner'
	_columns = {
		'property_delivery_carrier': fields.property(
		type='many2one',
		relation='delivery.grid',
		string="Delivery Method Grid",
		help="This delivery method will be used when invoicing from picking."),
	}

class sale_order(osv.Model):
	_inherit = 'sale.order'
	_columns = {
		'carrier_id': fields.many2one(
			"delivery.grid", string="Delivery Method",
			help="Complete this field if you plan to invoice the shipping based on picking."),
	}



	def delivery_set(self, cr, uid, ids, context=None):
		line_obj = self.pool.get('sale.order.line')
		grid_obj = self.pool.get('delivery.grid')
		carrier_obj = self.pool.get('delivery.carrier')
		acc_fp_obj = self.pool.get('account.fiscal.position')
		self._delivery_unset(cr, uid, ids, context=context)
		currency_obj = self.pool.get('res.currency')
		line_ids = []
		for order in self.browse(cr, uid, ids, context=context):
			grid_id = order.carrier_id.id
			if not grid_id:
				raise osv.except_osv(_('No Grid Available!'), _('No grid matching for this carrier!'))

			if order.state not in ('draft', 'sent'):
				raise osv.except_osv(_('Order not in Draft State!'), _('The order state have to be draft to add delivery lines.'))

			grid = grid_obj.browse(cr, uid, grid_id, context=context)

			taxes = grid.carrier_id.product_id.taxes_id.filtered(lambda t: t.company_id.id == order.company_id.id)
			fpos = order.fiscal_position or False
			taxes_ids = acc_fp_obj.map_tax(cr, uid, fpos, taxes, context=context)
			price_unit = grid_obj.get_price(cr, uid, grid.id, order, time.strftime('%Y-%m-%d'), context)
			if order.company_id.currency_id.id != order.pricelist_id.currency_id.id:
				price_unit = currency_obj.compute(cr, uid, order.company_id.currency_id.id, order.pricelist_id.currency_id.id,
					price_unit, context=dict(context or {}, date=order.date_order))
			values = {
				'order_id': order.id,
				'name': grid.carrier_id.name,
				'product_uom_qty': 1,
				'product_uom': grid.carrier_id.product_id.uom_id.id,
				'product_id': grid.carrier_id.product_id.id,
				'price_unit': price_unit,
				'tax_id': [(6, 0, taxes_ids)],
				'is_delivery': True,
			}
			res = line_obj.product_id_change(cr, uid, ids, order.pricelist_id.id, values['product_id'],
											qty=values['product_uom_qty'], uom=False, qty_uos=0, uos=False, name='', partner_id=order.partner_id.id,
											lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None)
			if res['value'].get('purchase_price'):
				values['purchase_price'] = res['value'].get('purchase_price')
			if order.order_line:
				values['sequence'] = order.order_line[-1].sequence + 1
			line_id = line_obj.create(cr, uid, values, context=context)
			line_ids.append(line_id)
		return line_ids

class stock_picking(osv.osv):
	_inherit = 'stock.picking'

	_columns = {
		'carrier_id': fields.many2one("delivery.grid", "Carrier")
	}

	def _prepare_shipping_invoice_line(self, cr, uid, picking, invoice, context=None):
		if picking.sale_id:
			delivery_line = picking.sale_id.order_line.filtered(lambda l: l.is_delivery and l.invoiced)
			if delivery_line:
				return None
		carrier_obj = self.pool.get('delivery.carrier')
		grid_obj = self.pool.get('delivery.grid')
		currency_obj = self.pool.get('res.currency')
		if not picking.carrier_id or \
			any(inv_line.product_id.id == picking.carrier_id.carrier_id.product_id.id
				for inv_line in invoice.invoice_line):
			return None
		grid_id = picking.carrier_id.id
		if not grid_id:
			raise osv.except_osv(_('Warning!'),_('The carrier has no delivery grid!'))
		quantity = sum([line.product_uom_qty for line in picking.move_lines])
		price = grid_obj.get_price_from_picking(cr, uid, grid_id,
				invoice.amount_untaxed, picking.weight, picking.volume,
				quantity, context=context)
		if invoice.company_id.currency_id.id != invoice.currency_id.id:
			price = currency_obj.compute(cr, uid, invoice.company_id.currency_id.id, invoice.currency_id.id,
				price, context=dict(context or {}, date=invoice.date_invoice))
		account_id = picking.carrier_id.carrier_id.product_id.property_account_income.id
		if not account_id:
			account_id = picking.carrier_id.carrier_id.product_id.categ_id\
				.property_account_income_categ.id

		taxes = picking.carrier_id.carrier_id.product_id.taxes_id
		partner = picking.partner_id or False
		fp = invoice.fiscal_position or partner.property_account_position
		if partner:
			account_id = self.pool.get('account.fiscal.position').map_account(cr, uid, fp, account_id)
			taxes_ids = self.pool.get('account.fiscal.position').map_tax(cr, uid, fp, taxes, context=context)
		else:
			taxes_ids = [x.id for x in taxes]

		return {
			'name': picking.carrier_id.carrier_id.name,
			'invoice_id': invoice.id,
			'uos_id': picking.carrier_id.carrier_id.product_id.uos_id.id,
			'product_id': picking.carrier_id.carrier_id.product_id.id,
			'account_id': account_id,
			'price_unit': price,
			'quantity': 1,
			'invoice_line_tax_id': [(6, 0, taxes_ids)],
		}

class account_invoice(osv.osv):
	_inherit = "account.invoice"

	_columns = {
		'carrier_id': fields.many2one('delivery.grid', string="Carrier id")
	}
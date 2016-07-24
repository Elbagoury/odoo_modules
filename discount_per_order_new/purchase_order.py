from openerp.osv import osv, fields
from openerp import api
import openerp.addons.decimal_precision as dp

class purchase_order_line_discount(osv.osv):
	_inherit = "purchase.order.line"

	def _calc_line_base_price(self, cr, uid, line, context=None):
		print "base_price"
		
		#if not line.order_id.discount_method or not line.order_id.po_discount:
		#	return line.price_unit * (1 - (line.discount or 0.0) / 100)

		untaxed = 0.0
		for l in line.order_id.order_line:
			untaxed += l.full_subtotal

		disc_percent = 0.0
		if line.order_id.discount_method == 'fixed':
			print 'fixed'
			disc_percent = line.order_id.po_discount * 100 / untaxed
		elif line.order_id.discount_method == 'percent':
			print 'percent'
			disc_percent = line.order_id.po_discount
		else:
			disc_percent = 0.0
		print disc_percent
		
		discount_gl_price = line.price_unit * (1 - (disc_percent or 0.0) / 100)
		discounted_final_price = discount_gl_price * (1 - (line.discount or 0.0) / 100)
		print discounted_final_price
		return discounted_final_price
		

	

	def _amount_full(self, cr, uid, ids, prop, arg, context=None):
		res = {}
		for line in self.browse(cr, uid, ids, context=context):
			discount_gl_price = line.price_unit * (1 - (line.discount_global or 0.0) / 100)
			full_subtotal = line.price_unit * line.product_qty
			res[line.id] = full_subtotal
		return res

	def _amount_with_disc(self, cr, uid, ids, prop, arg, context=None):
		res = {}
		for line in self.browse(cr, uid, ids, context=context):
			discount_gl_price = line.price_unit * (1 - (line.discount_global or 0.0) / 100)
			with_global_discount = discount_gl_price * line.product_qty
			res[line.id] = with_global_discount
		return res
	_columns = {
		'full_subtotal': fields.function(_amount_full, string="Full total", digits_compute= dp.get_precision('Account')),
		'with_global_discount': fields.function(_amount_with_disc, string="Subtotal with global discount", digits_compute= dp.get_precision('Account')),
		'discount_global': fields.float(string="Global discount"),
		'discount': fields.float(string="Discount (%)"),
		
	}
	
	
class PurchaseOrder(osv.osv):
	_inherit = "purchase.order"

	def change_discount(self, order):
		self = order
		if not self.discount_method or not self.po_discount:
			return

		untaxed = 0.0
		for l in self.order_line:
			untaxed += l.full_subtotal

		disc_percent = 0.0
		if self.discount_method == 'fixed':
			print 'fixed'
			disc_percent = self.po_discount * 100 / untaxed
		elif self.discount_method == 'percent':
			print 'percent'
			disc_percent = self.po_discount
		print disc_percent
		for l in self.order_line:
			print "setting global: %s" % disc_percent
			l.discount_global = disc_percent
			

	def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
		res = {}
		cur_obj=self.pool.get('res.currency')
		line_obj = self.pool['purchase.order.line']
		for order in self.browse(cr, uid, ids, context=context):
			#self.change_discount(order)
			res[order.id] = {
				'discount_amount': 0.0,
				'amount_untaxed': 0.0,
				'amount_tax': 0.0,
				'amount_total': 0.0,
			}
			
			untx = 0.0
			order_tax = None
			order_tax_amount = 0.0
			val = val1 = 0.0
			for line in order.order_line:
				untx += line.price_subtotal
				if line.taxes_id:
					order_tax = line.taxes_id
			if order_tax:
				order_tax_amount = order_tax.amount
			cur = order.pricelist_id.currency_id
			total = 0.0
			for line in order.order_line:
				print "IN MAIN:"
				print line.full_subtotal, line.discount_global, line.price_subtotal
				
				val1 += line.price_subtotal
				total += line.full_subtotal

				
				line_price = line_obj._calc_line_base_price(cr, uid, line, context=context)
				line_qty = line_obj._calc_line_quantity(cr, uid, line,context=context)
				
				for c in self.pool['account.tax'].compute_all(
						cr, uid, line.taxes_id, line_price, line_qty,
						line.product_id, order.partner_id)['taxes']:
					val += c.get('amount', 0.0)
			
			print total, val1, val, total-val1
			res[order.id]['discount_amount']= cur_obj.round(cr, uid, cur, total-val1)
			res[order.id]['amount_tax']= cur_obj.round(cr, uid, cur, val)
			res[order.id]['amount_untaxed']=cur_obj.round(cr, uid, cur, total)
			res[order.id]['discounted'] = cur_obj.round(cr, uid, cur, val1 or 0.0)
			res[order.id]['amount_total']=res[order.id]['discounted'] + res[order.id]['amount_tax']
			print res
		return res
	def _get_order(self, cr, uid, ids, context=None):
		result = {}
		for line in self.pool.get('purchase.order.line').browse(cr, uid, ids, context=context):
			result[line.order_id.id] = True
		return result.keys()

	_columns = {
		'discount_method': fields.selection([('fixed', "Fixed"), ('percent', 'Percent')], string="Discount method"),
		'po_discount': fields.float(string="PO discount"),
		'discount_amount': fields.function(_amount_all, digits_compute=dp.get_precision('Acount'), string="Discount",
			store={
				'purchase.order': (lambda self, cr, uid, ids, c={}:ids, ['po_discount', 'discount_method', 'order_line'], 10)
			}, multi="sums", track_visibility="always"),
		'discounted': fields.function(_amount_all, digits_compute=dp.get_precision("Account"), string="Amount with discount",
			store = {
				'purchase.order': (lambda self, cr, uid, ids, c={}:ids, ['po_discount', 'discount_method', 'discount_amount', 'order_line'], 10)
			}, multi="sums", track_visibility="always"),
		'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
			store={
				'purchase.order':(lambda self, cr, uid, ids, c={}:ids, ['po_discount', 'discount_method', 'order_line'], 10),
				'purchase.order.line': (_get_order, None, 10),
			}, multi="sums", help="The amount without tax", track_visibility='always'),
		'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Taxes',
			store={
				'purchase.order':(lambda self, cr, uid, ids, c={}:ids, ['po_discount', 'discount_method', 'order_line'], 10),
				'purchase.order.line': (_get_order, None, 10),
			}, multi="sums", help="The tax amount"),
		'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
			store={
				'purchase.order':(lambda self, cr, uid, ids, c={}:ids, ['po_discount', 'discount_method', 'order_line'], 10),
				'purchase.order.line': (_get_order, None, 10),
			}, multi="sums", help="The total amount"),
	}

	def _prepare_invoice(self, cr, uid, order, line_ids, context=None):
       
		journal_ids = self.pool['account.journal'].search(cr, uid, [('type', '=', 'purchase'),('company_id', '=', order.company_id.id)],limit=1)
		if not journal_ids:
			raise osv.except_osv(
				_('Error!'),
				_('Define purchase journal for this company: "%s" (id:%d).') % \
					(order.company_id.name, order.company_id.id))
		return {
			'name': order.partner_ref or order.name,
			'reference': order.partner_ref or order.name,
			'account_id': order.partner_id.property_account_payable.id,
			'type': 'in_invoice',
			'partner_id': order.partner_id.id,
			'currency_id': order.currency_id.id,
			'journal_id': len(journal_ids) and journal_ids[0] or False,
			'invoice_line': [(6, 0, line_ids)],
			'origin': order.name,
			'fiscal_position': order.fiscal_position.id or False,
			'payment_term': order.payment_term_id.id or False,
			'company_id': order.company_id.id,
			'discount_method': order.discount_method,
			'invoice_discount': order.po_discount,
		}

	def _prepare_inv_line(self, account_id, order_line):
		result = super(PurchaseOrder, self)._prepare_inv_line(
			account_id, order_line)
		result['discount'] = order_line.discount or 0.0
		return result
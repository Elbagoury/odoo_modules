"""
def _calc_line_base_price(self, cr, uid, line, context=None):
    line.full_subtotal = line.price_unit * line.product_uom_qty
    discounted_gl_price = line.price_unit * (1- (line.discount_global or 0.0) / 100)
    discounted_final_price = discounted_gl_price * (1 - (line.discount or 0.0) / 100.0)
    line.with_global_discount = discounted_gl_price * line.product_uom_qty

    line.product_price = line.product_id.list_price

    pricelist = line.order_id.pricelist_id
    discount_rate = 0
    if len(pricelist.version_id):
        version = pricelist.version_id[0]
        items = version.items_id
        qty = 0
        for item in items:
            if line.product_uom_qty >= item.min_quantity and item.min_quantity >= qty:
                discount_rate = (item.price_discount * -1) * 100
                qty = item.min_quantity
                #print "PRICELIST _____________", line.product_uom_qty, item.min_quantity, discount_rate

    line.pricelist_discount = discount_rate

    if line.is_manual_price:
        line.product_price = line.price_unit
        line.pricelist_discount = 0.0
    return discounted_final_price

def _do_calculations(self, cr, uid, ids, context=None):
    _logger = logging.getLogger(__name__)
    _logger.info("IN GET CALCULATIONS")
    lines = self.browse(cr, uid, ids, context=None)
    for line in lines:
        line.full_subtotal = line.price_unit * line.product_uom_qty


        discounted_gl_price = line.price_unit * (1- (line.discount_global or 0.0) / 100)
        discounted_final_price = discounted_gl_price * (1 - (line.discount or 0.0) / 100.0)
        line.with_global_discount = discounted_gl_price * line.product_uom_qty

        line.product_price = line.product_id.list_price

        pricelist = line.order_id.pricelist_id
        discount_rate = 0
        if len(pricelist.version_id):
            version = pricelist.version_id[0]
            items = version.items_id
            qty = 0
            for item in items:
                if line.product_uom_qty >= item.min_quantity and item.min_quantity >= qty:
                    discount_rate = (item.price_discount * -1) * 100
                    qty = item.min_quantity
                    #print "PRICELIST _____________", line.product_uom_qty, item.min_quantity, discount_rate

        line.pricelist_discount = discount_rate

        if line.is_manual_price:
            line.product_price = line.price_unit
            line.pricelist_discount = 0.0

        line.price_subtotal = discounted_final_price
        _logger.info("-------DISCOUNT PRICELIST %s" % line.pricelist_discount)
        self.write(cr, uid, line.id, {'product_price': line.product_price, 'pricelist_discount': line.pricelist_discount, 'full_subtotal': line.full_subtotal, 'with_global_discount': line.with_global_discount}, context=None)


        return line.product_price, line.pricelist_discount, line.price_subtotal, line.full_subtotal, line.with_global_discount
"""

"""
    'amount_untaxed': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
        store={
            'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_discount', 'order_line', 'order_line.price_subtotal', 'order_line.discount_global', 'discount_method'], 10),

            'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
        },
        multi='sums', help="The amount without tax.", track_visibility='always'),
    'amount_tax': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='Taxes',
        store={
            'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_discount', 'order_line', 'order_line.price_subtotal', 'order_line.discount_global','discount_method'], 10),

            'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
        },
        multi='sums', help="The tax amount."),
    'amount_discount': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='Discount',
        store={
            'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_discount', 'order_line', 'order_line.price_subtotal', 'order_line.discount_global','discount_method'], 10),
        },
        multi='sums', track_visibility="always"),
    'discounted': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string="Amount with discount",
        store={
            'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['amount_discount','order_discount', 'order_line', 'order_line.price_subtotal', 'order_line.discount_global','discount_method'], 10),
        },
        multi='sums', track_visibility="always"),
    'amount_total': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='Total',
        store={
            'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_discount', 'order_line', 'order_line.price_subtotal', 'order_line.discount_global','discount_method'], 10),

            'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
        },
        multi='sums', help="The total amount."),
"""

#
### ALL
from openerp.osv import osv, fields
from openerp import api#fields, models, api, _
import openerp.addons.decimal_precision as dp
import logging


class order_line_discount(osv.osv):
	_inherit = "sale.order.line"

	def _product_price(self, cr, uid, ids, field_name, arg, context=None):
		print "1"

		res={}
		for line in self.browse(cr, uid, ids, context=context):
			product_price = line.product_id.list_price
			if line.is_manual_price:
				product_price = line.price_unit

			res[line.id] = product_price
			print res
			return res
	"""
	def _pricelist_discount(self, cr, uid, ids, field_name, arg, context=None):
		print "2"

		res={}
		for line in self.browse(cr, uid, ids, context=context):
			pricelist = line.order_id.pricelist_id
			discount_rate = 0
			if len(pricelist.version_id):
				version = pricelist.version_id[0]
				items = version.items_id
				qty = 0
				for item in items:
					if line.product_uom_qty >= item.min_quantity and item.min_quantity >= qty:
						discount_rate = (item.price_discount * -1) * 100
						qty = item.min_quantity
						#print "PRICELIST _____________", line.product_uom_qty, item.min_quantity, discount_rate

			pricelist_discount = discount_rate
			res[line.id] = pricelist_discount
			return res
	def _full_subtotal(self, cr, uid, ids, field_name, arg, context=None):
		print "3"
		return 3
		res={}
		for line in self.browse(cr, uid, ids, context=context):
			full_subtotal = line.price_unit * line.product_uom_qty
			res[line.id] = full_subtotal
			return res

	def _with_global_discount(self, cr, uid, ids, field_name, arg, context=None):
		print "4"
		return 2
		res={}
		for line in self.browse(cr, uid, ids, context=context):
			with_global_discount = discounted_gl_price * line.product_uom_qty
			res[line.id] = with_global_discount
			return res

	def _global_discount(self, cr, uid, ids, field_name, arg, context=None):
		print "5"
		return 1

		res = {}
		untaxed = 0.0
		for l in self.browse(cr, uid, ids, context=context):

			untaxed += l.full_subtotal

			if l.order_id.discount_method == 'fixed':

				disc_percent = (l.order_id.order_discount or 0.0) * 100 / untaxed
			elif l.order_id.discount_method == 'percent':

				disc_percent = l.order_id.order_discount or 0.0
			else:
				disc_percent = 0.0
			res[line.id] = disc_percent
		for l in self.browse(cr, uid, ids, context=context):
			l.discount_global = disc_percent

			return res
	"""
	_columns = {
		'product_price':fields.function(_product_price, string='Full price', digits_compute= dp.get_precision('Account')),
		'pricelist_discount': fields.float(),#fields.function(_pricelist_discount, string='Pricelist discount', digits_compute= dp.get_precision('Account')),
		'full_subtotal': fields.float(),#fields.function(_full_subtotal, string='Full Subtotal', digits_compute= dp.get_precision('Account')),
		'with_global_discount': fields.float(),#fields.function(_with_global_discount, string='With global discount', digits_compute= dp.get_precision('Account')),
		'discount_global': fields.float(string='Subtotal'),
		'is_manual_price': fields.boolean(string="Manual price")
	}


class order_discount(osv.osv):
	_inherit = "sale.order"

	"""
	def _amount_all_wrapper(self, cr, uid, ids, field_name, arg, context=None):

		return self._amount_all(cr, uid, ids, field_name, arg, context=context)

	def _amount_all(self, cr, uid, ids, field_name=None, arg=None, context=None, update=None):

		cur_obj = self.pool.get('res.currency')
		res = {}
		for order in self.browse(cr, uid, ids, context=context):


			res[order.id] = {
				'amount_discount':0.0,
				'amount_untaxed': 0.0,
				'amount_tax': 0.0,
				'amount_total': 0.0,
			}
			val = val1 = 0.0

			untx = 0.0

			order_tax = None
			order_tax_amount = 0.0

			for line in order.order_line:
				untx += line.price_subtotal

				if line.tax_id:
					order_tax = line.tax_id
			if order_tax:
				order_tax_amount = order_tax.amount
			#print order_tax.name, order_tax.amount or "NO TAX"

			method = order.discount_method

			disc = 0
			order_disc_percent = 0.0
			#if method:
			#	if method == 'fixed':
			#		disc = order.order_discount
			#		order_disc_percent = (disc * 100) / untx
			#	elif method == 'percent':
			#		disc = untx * (order.order_discount /100)
			#		order_disc_percent = order.order_discount
			#	print disc
			#	print order_disc_percent

			if order_disc_percent:
				l_ids = []
				for line in order.order_line:
					l_ids.append(line.id)


			cur = order.pricelist_id.currency_id
			total = 0.0

			discounted = 0

			res[order.id]['amount_discount'] = cur_obj.round(cr, uid, cur, total - val1)
			res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
			res[order.id]['amount_untaxed'] = cur_obj.round(cr, uid, cur, total)
			res[order.id]['discounted'] = val1 or 0.0
			res[order.id]['amount_total'] = res[order.id]['discounted'] + res[order.id]['amount_tax']

			#_logger.info('----- %s' % res)

		return res

	def _get_order(self, cr, uid, ids, context=None):
		result = {}
		for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
			result[line.order_id.id] = True
		return result.keys()
	"""
	_columns = {
		'discount_method': fields.selection([('fixed','Fixed'), ('percent','Percent')], string="Discount method"),
		'order_discount': fields.float(string="Discount"),

	}


	def _prepare_invoice(self, cr, uid, order, lines, context=None):

		print "PREPARING INVOICE"
		sale_order = self.pool.get('sale.order').browse(cr, uid, order.id, context=None)[0]


		for line in lines:
			for l in sale_order.order_line:

				ln = self.pool.get('account.invoice.line').browse(cr, uid, line, context=None)
				if ln.product_id.id == l.product_id.id and ln.name == l.name and ln.quantity == l.product_uom_qty:
					ln.product_price = l.product_price
					ln.pricelist_discount = l.pricelist_discount
					print "found", ln.product_price



		if context is None:
			context = {}
		journal_id = self.pool['account.invoice'].default_get(cr, uid, ['journal_id'], context=context)['journal_id']
		if not journal_id:
			raise osv.except_osv(_('Error!'),
				_('Please define sales journal for this company: "%s" (id:%d).') % (order.company_id.name, order.company_id.id))
		invoice_vals = {
			'name': order.client_order_ref or '',
			'origin': order.name,
			'type': 'out_invoice',
			'reference': order.client_order_ref or order.name,
			'account_id': order.partner_invoice_id.property_account_receivable.id,
			'partner_id': order.partner_invoice_id.id,
			'journal_id': journal_id,
			'invoice_line': [(6, 0, lines)],
			'currency_id': order.pricelist_id.currency_id.id,
			'comment': order.note,
			'payment_term': order.payment_term and order.payment_term.id or False,
			'fiscal_position': order.fiscal_position.id or order.partner_invoice_id.property_account_position.id,
			'date_invoice': context.get('date_invoice', False),
			'company_id': order.company_id.id,
			'user_id': order.user_id and order.user_id.id or False,
			'section_id' : order.section_id.id,
			'invoice_discount': order.order_discount,
			'discount_method': order.discount_method,
			'our_bank':order.partner_id.our_bank.id if order.partner_id.our_bank else None,
			'goods_description_id': order.goods_description_id.id if order.goods_description_id else None,
			'carriage_condition_id': order.carriage_condition_id.id if order.carriage_condition_id else None,
			'transportation_reason_id': order.transportation_reason_id.id if order.transportation_reason_id else None,
			'transportation_method_id': order.transportation_method_id.id if order.transportation_method_id else None,
			'parcels': order.parcels,

		}

		# Care for deprecated _inv_get() hook - FIXME: to be removed after 6.1
		invoice_vals.update(self._inv_get(cr, uid, order, context=context))
		return invoice_vals

	def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):

		res = {}
		if not line.invoiced:
			if not account_id:
				if line.product_id:
					account_id = line.product_id.property_account_income.id
					if not account_id:
						account_id = line.product_id.categ_id.property_account_income_categ.id
					if not account_id:
						raise osv.except_osv(_('Error!'),
								_('Please define income account for this product: "%s" (id:%d).') % \
									(line.product_id.name, line.product_id.id,))
				else:
					prop = self.pool.get('ir.property').get(cr, uid,
						'property_account_income_categ', 'product.category',
							context=context)
					account_id = prop and prop.id or False
			uosqty = self._get_line_qty(cr, uid, line, context=context)
			uos_id = self._get_line_uom(cr, uid, line, context=context)
			pu = 0.0
			if uosqty:
				pu = round(line.price_unit * line.product_uom_qty / uosqty,
					self.pool.get('decimal.precision').precision_get(cr, uid, 'Product Price'))
			fpos = line.order_id.fiscal_position or False
			account_id = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, account_id)
			if not account_id:
				raise osv.except_osv(_('Error!'),
						_('There is no Fiscal Position defined or Income category account defined for default properties of Product categories.'))
			res = {
				'name': line.name,
				'sequence': line.sequence,
				'origin': line.order_id.name,
				'account_id': account_id,
				'price_unit': pu,
				'product_price': line.product_price,
				'pricelist_discount': line.pricelist_discount,
				'quantity': uosqty,
				'discount': line.discount,
				'uos_id': uos_id,
				'product_id': line.product_id.id or False,
				'invoice_line_tax_id': [(6, 0, [x.id for x in line.tax_id])],
				'account_analytic_id': line.order_id.project_id and line.order_id.project_id.id or False,
			}

		return res

class StockMove(osv.osv):
	_inherit = "stock.move"

	def _create_invoice_line_from_vals(self, cr, uid, move, invoice_line_vals, context=None):
		_logger = logging.getLogger(__name__)
		print "Stock.move _create_invoice_line_from_vals"
		sale_line = move.procurement_id.sale_line_id
		#_logger.info("********* CREATE INVOICE LINE VALS: %s, %s, %s" % (sale_line.product_price, sale_line.pricelist_discount, sale_line.price_unit))
		if sale_line:
			invoice_line_vals['product_price'] = sale_line.product_price
			invoice_line_vals['pricelist_discount'] = sale_line.pricelist_discount
		else:
			invoice_line_vals['product_price'] = invoice_line_vals['price_unit']
			invoice_line_vals['pricelist_discount'] = 0.0
		#_logger.info("******** CREATE INVOICE FROM LINES: %s" % invoice_line_vals)
		invoice_line_id = super(StockMove, self)._create_invoice_line_from_vals(cr, uid, move, invoice_line_vals, context=context)
		if context.get('inv_type') in ('out_invoice', 'out_refund') and move.procurement_id and move.procurement_id.sale_line_id:
			sale_line = move.procurement_id.sale_line_id
			self.pool.get('sale.order.line').write(cr, uid, [sale_line.id], {
				'invoice_lines': [(4, invoice_line_id)]
			}, context=context)
			self.pool.get('sale.order').write(cr, uid, [sale_line.order_id.id], {
				'invoice_ids': [(4, invoice_line_vals['invoice_id'])],
			})
			sale_line_obj = self.pool.get('sale.order.line')
			invoice_line_obj = self.pool.get('account.invoice.line')
			sale_line_ids = sale_line_obj.search(cr, uid, [('order_id', '=', move.procurement_id.sale_line_id.order_id.id), ('invoiced', '=', False), '|', ('product_id', '=', False), ('product_id.type', '=', 'service')], context=context)
			if sale_line_ids:
				created_lines = sale_line_obj.invoice_line_create(cr, uid, sale_line_ids, context=context)
				invoice_line_obj.write(cr, uid, created_lines, {'invoice_id': invoice_line_vals['invoice_id']}, context=context)

		return invoice_line_id

	def _get_price_unit_invoice(self, cr, uid, move_line, type, context=None):
		""" Gets price unit for invoice
		@param move_line: Stock move lines
		@param type: Type of invoice
		@return: The price unit for the move line
		"""
		_logger = logging.getLogger(__name__)
		print "Stock.move _get_price_unit_invoice"

		if context is None:
			context = {}
		if type in ('in_invoice', 'in_refund'):
			#_logger.info("RETURNING %s" % move_line.price_unit)
			return move_line.price_unit, 0
		else:
			# If partner given, search price in its sale pricelist
			if move_line.partner_id and move_line.partner_id.property_product_pricelist:
				pricelist_obj = self.pool.get("product.pricelist")
				pl = move_line.partner_id.property_product_pricelist
				pricelist = pl.id

				discount_rate = 0
				if len(pl.version_id):
					version = pl.version_id[0]
					items = version.items_id
					qty = 0
					for item in items:
						if move_line.product_uom_qty >= item.min_quantity and item.min_quantity >= qty:
							discount_rate = (item.price_discount * -1) * 100
							qty = item.min_quantity
				price = pricelist_obj.price_get(cr, uid, [pricelist],
						move_line.product_id.id, move_line.product_uom_qty, move_line.partner_id.id, {
							'uom': move_line.product_uom.id,
							'date': move_line.date,
						})[pricelist]
				if price:

					return price, discount_rate
		return move_line.product_id.list_price, 0


	def _get_invoice_line_vals(self, cr, uid, move, partner, inv_type, context=None):

		_logger = logging.getLogger(__name__)
		print "Stock.move _get_invoice_line_vals"

		res = super(StockMove, self)._get_invoice_line_vals(cr, uid, move, partner, inv_type)

		####

		price_unit, pricelist_discount = self._get_price_unit_invoice(cr, uid, move, inv_type)


		pp = price_unit
		if pricelist_discount > 0:
			pp = (pp * 100) / (100 - pricelist_discount)

		res.update({
				'price_unit': price_unit,
				'pricelist_discount': pricelist_discount,
				'product_price': pp
			})

		return res

class stock_pck_test(osv.osv):
	_inherit = "stock.picking"

	def _get_invoice_vals(self, cr, uid, key, inv_type, journal_id, move, context=None):
		_logger = logging.getLogger(__name__)
		_logger.info("Stock.picking _get_invoice_vals")

		if context is None:
			context = {}
		partner, currency_id, company_id, user_id = key
		if inv_type in ('out_invoice', 'out_refund'):
			account_id = partner.property_account_receivable.id
			payment_term = partner.property_payment_term.id or False
		else:
			account_id = partner.property_account_payable.id
			payment_term = partner.property_supplier_payment_term.id or False

		discount_method = move.picking_id.sale_id.discount_method or None
		discount = move.picking_id.sale_id.order_discount or 0.0
		user_id = uid
		valx = {
			'origin': move.picking_id.name,
			'date_invoice': context.get('date_inv', False),
			'user_id': user_id,
			'partner_id': partner.id,
			'account_id': account_id,
			'payment_term': payment_term,
			'discount_method': discount_method,
			'invoice_discount': discount,
			'type': inv_type,
			'fiscal_position': partner.property_account_position.id,
			'company_id': company_id,
			'currency_id': currency_id,
			'journal_id': journal_id,
			'our_bank':partner.our_bank.id if partner.our_bank else None,
			'goods_description_id': partner.goods_description_id.id if partner.goods_description_id else None,
			'carriage_condition_id': partner.carriage_condition_id.id if partner.carriage_condition_id else None,
			'transportation_reason_id': partner.transportation_reason_id.id if partner.transportation_reason_id else None,
			'transportation_method_id': partner.transportation_method_id.id if partner.transportation_method_id else None,
			'parcels': move.picking_id.sale_id.parcels if move.picking_id and move.picking_id.sale_id else 0,
			'partner_bank_id': partner.bank_ids[0].id if partner.bank_ids else None
		}
		_logger.info(valx)
		return valx


	def _invoice_create_line(self, cr, uid, moves, journal_id, inv_type='out_invoice', context=None):
		_logger = logging.getLogger(__name__)
		_logger.info("IN FIRST")
		invoice_obj = self.pool.get('account.invoice')
		move_obj = self.pool.get('stock.move')
		invoices = {}
		is_extra_move, extra_move_tax = move_obj._get_moves_taxes(cr, uid, moves, inv_type, context=context)
		product_price_unit = {}
		for move in moves:
			company = move.company_id
			origin = move.picking_id.name
			partner, user_id, currency_id = move_obj._get_master_data(cr, uid, move, company, context=context)
			user_id = uid
			key = (partner, currency_id, company.id, user_id)
			print "KEY"
			print key
			invoice_vals = self._get_invoice_vals(cr, uid, key, inv_type, journal_id, move, context=context)

			if key not in invoices:
				# Get account and payment terms
				invoice_id = self._create_invoice_from_picking(cr, uid, move.picking_id, invoice_vals, context=context)
				invoices[key] = invoice_id
			else:
				invoice = invoice_obj.browse(cr, uid, invoices[key], context=context)
				merge_vals = {}
				if not invoice.origin or invoice_vals['origin'] not in invoice.origin.split(', '):
					invoice_origin = filter(None, [invoice.origin, invoice_vals['origin']])
					merge_vals['origin'] = ', '.join(invoice_origin)
				if invoice_vals.get('name', False) and (not invoice.name or invoice_vals['name'] not in invoice.name.split(', ')):
					invoice_name = filter(None, [invoice.name, invoice_vals['name']])
					merge_vals['name'] = ', '.join(invoice_name)
				if merge_vals:
					invoice.write(merge_vals)
			invoice_line_vals = move_obj._get_invoice_line_vals(cr, uid, move, partner, inv_type, context=dict(context, fp_id=invoice_vals.get('fiscal_position', False)))
			invoice_line_vals['invoice_id'] = invoices[key]
			invoice_line_vals['origin'] = origin
			if not is_extra_move[move.id]:
				product_price_unit[invoice_line_vals['product_id'], invoice_line_vals['uos_id']] = invoice_line_vals['price_unit']
			if is_extra_move[move.id] and (invoice_line_vals['product_id'], invoice_line_vals['uos_id']) in product_price_unit:
				invoice_line_vals['price_unit'] = product_price_unit[invoice_line_vals['product_id'], invoice_line_vals['uos_id']]
			if is_extra_move[move.id]:
				desc = (inv_type in ('out_invoice', 'out_refund') and move.product_id.product_tmpl_id.description_sale) or \
					(inv_type in ('in_invoice','in_refund') and move.product_id.product_tmpl_id.description_purchase)
				invoice_line_vals['name'] += ' ' + desc if desc else ''
				if extra_move_tax[move.picking_id, move.product_id]:
					invoice_line_vals['invoice_line_tax_id'] = extra_move_tax[move.picking_id, move.product_id]
				#the default product taxes
				elif (0, move.product_id) in extra_move_tax:
					invoice_line_vals['invoice_line_tax_id'] = extra_move_tax[0, move.product_id]

			move_obj._create_invoice_line_from_vals(cr, uid, move, invoice_line_vals, context=context)
			move_obj.write(cr, uid, move.id, {'invoice_state': 'invoiced'}, context=context)

		invoice_obj.button_compute(cr, uid, invoices.values(), context=context, set_total=(inv_type in ('in_invoice', 'in_refund')))
		return invoices.values()


        ###

        <?xml version="1.0" encoding="UTF-8"?>
        	<openerp>
        		<data>
        			<record id="order_discount" model="ir.ui.view">
        				<field name="name">order.discount.form</field>
        				<field name="model">sale.order</field>
        				<field name="inherit_id" ref="sale.view_order_form" />
        				<field name="arch" type="xml">
        						<xpath expr="//field[@name='amount_untaxed']" position="after">
        						</xpath>
        					<!--
        					<xpath expr="//field[@name='amount_untaxed']" position="after">

        							<field name="amount_discount" widget="monetary"/>
        							<field name="discounted" widget="monetary"/>
        					</xpath >-->
        					<xpath expr="//tree[@string='Sales Order Lines']/field[@name='price_unit']" position="before">

        							<field name="product_price"/>
        							<!--<field name="pricelist_discount"/>-->


        					</xpath>
        					<!--
        					<xpath expr="//form[@string='Sales Order Lines']/group/group/field[@name='price_unit']" position="before">

        							<field name="product_price"/>
        							<field name="pricelist_discount" readonly="1"/>
        							<field name="is_manual_price"/>




        					</xpath>
        					<xpath expr="//form[@string='Sales Order Lines']/field[@name='name']" position="before">
        						<group>
        								<button type="object" name="cancel_pricelist_discount" string="Remove pricelist discount" attrs="{'invisible':['|', ('state', 'not in', 'draft'), ('pricelist_discount', '=', 0.0)]}"/>
        							</group>
        					</xpath>
        					<xpath expr="//field[@name='note']" position="before">
        						<group >
        							<field name="discount_method" style="width:100px;" />
        							<field name="order_discount" />

        						</group>


        					</xpath>
        					-->
        				</field>
        				</record>
        				<record id="order_line_discount" model="ir.ui.view">
        					<field name="name">order.discount.line.form</field>
        					<field name="model">sale.order.line</field>
        					<field name="inherit_id" ref="sale.view_order_line_form2" />
        					<field name="arch" type="xml">
        						<xpath expr="//field[@name='discount']" position="after">

        								<!--<field name="pricelist_discount"/>
        								<field name="is_manual_price"/>-->

        						</xpath >

        					</field>
        					</record>

        		</data>
        	</openerp>

#
class StockMove(models.Model):
	_inherit = "stock.move"

	def _create_invoice_line_from_vals(self, cr, uid, move, invoice_line_vals, context=None):
		_logger = logging.getLogger(__name__)
		print "Stock.move _create_invoice_line_from_vals"
		sale_line = move.procurement_id.sale_line_id
		#_logger.info("********* CREATE INVOICE LINE VALS: %s, %s, %s" % (sale_line.product_price, sale_line.pricelist_discount, sale_line.price_unit))
		if sale_line:
			invoice_line_vals['product_price'] = sale_line.product_price
			invoice_line_vals['pricelist_discount'] = sale_line.pricelist_discount
		else:
			invoice_line_vals['product_price'] = invoice_line_vals['price_unit']
			invoice_line_vals['pricelist_discount'] = 0.0
		#_logger.info("******** CREATE INVOICE FROM LINES: %s" % invoice_line_vals)
		invoice_line_id = super(StockMove, self)._create_invoice_line_from_vals(cr, uid, move, invoice_line_vals, context=context)
		if context.get('inv_type') in ('out_invoice', 'out_refund') and move.procurement_id and move.procurement_id.sale_line_id:
			sale_line = move.procurement_id.sale_line_id
			self.pool.get('sale.order.line').write(cr, uid, [sale_line.id], {
				'invoice_lines': [(4, invoice_line_id)]
			}, context=context)
			self.pool.get('sale.order').write(cr, uid, [sale_line.order_id.id], {
				'invoice_ids': [(4, invoice_line_vals['invoice_id'])],
			})
			sale_line_obj = self.pool.get('sale.order.line')
			invoice_line_obj = self.pool.get('account.invoice.line')
			sale_line_ids = sale_line_obj.search(cr, uid, [('order_id', '=', move.procurement_id.sale_line_id.order_id.id), ('invoiced', '=', False), '|', ('product_id', '=', False), ('product_id.type', '=', 'service')], context=context)
			if sale_line_ids:
				created_lines = sale_line_obj.invoice_line_create(cr, uid, sale_line_ids, context=context)
				invoice_line_obj.write(cr, uid, created_lines, {'invoice_id': invoice_line_vals['invoice_id']}, context=context)

		return invoice_line_id

	def _get_price_unit_invoice(self, cr, uid, move_line, type, context=None):

		_logger = logging.getLogger(__name__)
		print "Stock.move _get_price_unit_invoice"

		if context is None:
			context = {}
		if type in ('in_invoice', 'in_refund'):
			#_logger.info("RETURNING %s" % move_line.price_unit)
			return move_line.price_unit, 0
		else:
			# If partner given, search price in its sale pricelist
			if move_line.partner_id and move_line.partner_id.property_product_pricelist:
				pricelist_obj = self.pool.get("product.pricelist")
				pl = move_line.partner_id.property_product_pricelist
				pricelist = pl.id

				discount_rate = 0
				if len(pl.version_id):
					version = pl.version_id[0]
					items = version.items_id
					qty = 0
					for item in items:
						if move_line.product_uom_qty >= item.min_quantity and item.min_quantity >= qty:
							discount_rate = (item.price_discount * -1) * 100
							qty = item.min_quantity
				price = pricelist_obj.price_get(cr, uid, [pricelist],
						move_line.product_id.id, move_line.product_uom_qty, move_line.partner_id.id, {
							'uom': move_line.product_uom.id,
							'date': move_line.date,
						})[pricelist]
				if price:

					return price, discount_rate
		return move_line.product_id.list_price, 0


	def _get_invoice_line_vals(self, cr, uid, move, partner, inv_type, context=None):

		_logger = logging.getLogger(__name__)
		print "Stock.move _get_invoice_line_vals"

		res = super(StockMove, self)._get_invoice_line_vals(cr, uid, move, partner, inv_type)

		####

		price_unit, pricelist_discount = self._get_price_unit_invoice(cr, uid, move, inv_type)


		pp = price_unit
		if pricelist_discount > 0:
			pp = (pp * 100) / (100 - pricelist_discount)

		res.update({
				'price_unit': price_unit,
				'pricelist_discount': pricelist_discount,
				'product_price': pp
			})

		return res

class stock_pck_test(models.Model):
	_inherit = "stock.picking"

	def _get_invoice_vals(self, cr, uid, key, inv_type, journal_id, move, context=None):
		_logger = logging.getLogger(__name__)
		_logger.info("Stock.picking _get_invoice_vals")

		if context is None:
			context = {}
		partner, currency_id, company_id, user_id = key
		if inv_type in ('out_invoice', 'out_refund'):
			account_id = partner.property_account_receivable.id
			payment_term = partner.property_payment_term.id or False
		else:
			account_id = partner.property_account_payable.id
			payment_term = partner.property_supplier_payment_term.id or False

		discount_method = move.picking_id.sale_id.discount_method or None
		discount = move.picking_id.sale_id.order_discount or 0.0
		user_id = uid
		valx = {
			'origin': move.picking_id.name,
			'date_invoice': context.get('date_inv', False),
			'user_id': user_id,
			'partner_id': partner.id,
			'account_id': account_id,
			'payment_term': payment_term,
			'discount_method': discount_method,
			'invoice_discount': discount,
			'type': inv_type,
			'fiscal_position': partner.property_account_position.id,
			'company_id': company_id,
			'currency_id': currency_id,
			'journal_id': journal_id,
			'our_bank':partner.our_bank.id if partner.our_bank else None,
			'goods_description_id': partner.goods_description_id.id if partner.goods_description_id else None,
			'carriage_condition_id': partner.carriage_condition_id.id if partner.carriage_condition_id else None,
			'transportation_reason_id': partner.transportation_reason_id.id if partner.transportation_reason_id else None,
			'transportation_method_id': partner.transportation_method_id.id if partner.transportation_method_id else None,
			'parcels': move.picking_id.sale_id.parcels if move.picking_id and move.picking_id.sale_id else 0,
			'partner_bank_id': partner.bank_ids[0].id if partner.bank_ids else None
		}
		_logger.info(valx)
		return valx


	def _invoice_create_line(self, cr, uid, moves, journal_id, inv_type='out_invoice', context=None):
		_logger = logging.getLogger(__name__)
		_logger.info("IN FIRST")
		invoice_obj = self.pool.get('account.invoice')
		move_obj = self.pool.get('stock.move')
		invoices = {}
		is_extra_move, extra_move_tax = move_obj._get_moves_taxes(cr, uid, moves, inv_type, context=context)
		product_price_unit = {}
		for move in moves:
			company = move.company_id
			origin = move.picking_id.name
			partner, user_id, currency_id = move_obj._get_master_data(cr, uid, move, company, context=context)
			user_id = uid
			key = (partner, currency_id, company.id, user_id)
			print "KEY"
			print key
			invoice_vals = self._get_invoice_vals(cr, uid, key, inv_type, journal_id, move, context=context)

			if key not in invoices:
				# Get account and payment terms
				invoice_id = self._create_invoice_from_picking(cr, uid, move.picking_id, invoice_vals, context=context)
				invoices[key] = invoice_id
			else:
				invoice = invoice_obj.browse(cr, uid, invoices[key], context=context)
				merge_vals = {}
				if not invoice.origin or invoice_vals['origin'] not in invoice.origin.split(', '):
					invoice_origin = filter(None, [invoice.origin, invoice_vals['origin']])
					merge_vals['origin'] = ', '.join(invoice_origin)
				if invoice_vals.get('name', False) and (not invoice.name or invoice_vals['name'] not in invoice.name.split(', ')):
					invoice_name = filter(None, [invoice.name, invoice_vals['name']])
					merge_vals['name'] = ', '.join(invoice_name)
				if merge_vals:
					invoice.write(merge_vals)
			invoice_line_vals = move_obj._get_invoice_line_vals(cr, uid, move, partner, inv_type, context=dict(context, fp_id=invoice_vals.get('fiscal_position', False)))
			invoice_line_vals['invoice_id'] = invoices[key]
			invoice_line_vals['origin'] = origin
			if not is_extra_move[move.id]:
				product_price_unit[invoice_line_vals['product_id'], invoice_line_vals['uos_id']] = invoice_line_vals['price_unit']
			if is_extra_move[move.id] and (invoice_line_vals['product_id'], invoice_line_vals['uos_id']) in product_price_unit:
				invoice_line_vals['price_unit'] = product_price_unit[invoice_line_vals['product_id'], invoice_line_vals['uos_id']]
			if is_extra_move[move.id]:
				desc = (inv_type in ('out_invoice', 'out_refund') and move.product_id.product_tmpl_id.description_sale) or \
					(inv_type in ('in_invoice','in_refund') and move.product_id.product_tmpl_id.description_purchase)
				invoice_line_vals['name'] += ' ' + desc if desc else ''
				if extra_move_tax[move.picking_id, move.product_id]:
					invoice_line_vals['invoice_line_tax_id'] = extra_move_tax[move.picking_id, move.product_id]
				#the default product taxes
				elif (0, move.product_id) in extra_move_tax:
					invoice_line_vals['invoice_line_tax_id'] = extra_move_tax[0, move.product_id]

			move_obj._create_invoice_line_from_vals(cr, uid, move, invoice_line_vals, context=context)
			move_obj.write(cr, uid, move.id, {'invoice_state': 'invoiced'}, context=context)

		invoice_obj.button_compute(cr, uid, invoices.values(), context=context, set_total=(inv_type in ('in_invoice', 'in_refund')))
		return invoices.values()

from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
import logging
from datetime import datetime

class SaleOrderLine(models.Model):
	_inherit = "sale.order.line"

	price_subtotal = fields.Float(compute="_compute_values", string="Subtotal")
	full_subtotal = fields.Float(compute="_compute_values", string="Full subtotal")
	with_discount = fields.Float(compute="_compute_values", string="With discount")
	discount_global = fields.Float(compute="_compute_values", string="Global discount")
	product_price = fields.Float(compute="_compute_values", string="Full price")
	pricelist_discount = fields.Float(compute="_compute_values", string="Pricelist discount (%)")
	is_manual_price = fields.Boolean(string="Manual price")
	custom_note = fields.Char(string="Custom note")



	@api.multi
	#@api.depends('price_unit', 'discount_global', 'order_id.discount_method', 'order_id.order_discount', 'product_uom_qty',
	#	'product_id', 'order_id.partner_id')
	def _compute_values(self):
		#print "_compute_values"
		untx = 0

		for line in self:
			if line.price_unit == 0:
				continue
			untx += line.price_unit * line.product_uom_qty
		for line in self:
			if line.price_unit == 0:
				continue
			#print line.product_id.name
			if not line.price_unit or not line.product_uom_qty:

				return True

			tax_obj = line.pool.get('account.tax')
			cur_obj = line.pool.get('res.currency')
			if line.order_id:
				if line.order_id.discount_method == 'percent':
					line.discount_global = line.order_id.order_discount
				elif line.order_id.discount_method == 'fixed':
					#print "fixed"
					#print untx
					line.discount_global = (line.order_id.order_discount * 100 / untx) or 1
				else:
					line.discount_global = 0.0
			price_with_global = line.price_unit * (1 - (line.discount_global or 0.0) / 100.00)
			price = price_with_global * (1 - (line.discount or 0.0) / 100.0)

			line.with_discount = price_with_global
			line.full_subtotal = line.price_unit * line.product_uom_qty
			taxes = tax_obj.compute_all(line._cr, line._uid, line.tax_id, price, line.product_uom_qty,
	                                        line.product_id,
	                                        line.order_id.partner_id)
			cur = line.order_id.pricelist_id.currency_id

			line.price_subtotal = cur_obj.round(line._cr, line._uid, cur, taxes['total'])
			product_price = 0
			pricelist_disc = 0
			if line.is_manual_price:
				#print "MANUAL"
				product_price = line.price_unit
				pricelist_disc = 0.0
			else:
				#print "NOT MANUAL"
				pricelist = line.order_id.pricelist_id

				discount_rate = 0
				if len(pricelist.version_id):

					categ_ids = {}
					if line.product_id:
						categ = line.product_id.categ_id
						while categ:
							categ_ids[categ.id] = True
							categ = categ.parent_id
						categ_ids = categ_ids.keys()


					items = pricelist.version_id[0].items_id

					qty = 0
					for item in items:
						if item.categ_id.id and item.categ_id.id not in categ_ids:
							continue
						if line.product_uom_qty >= item.min_quantity and item.min_quantity >= qty:
							discount_rate = (item.price_discount * -1) * 100
							qty = item.min_quantity

							product_price = line.product_id.list_price
							pricelist_disc = discount_rate



			line.product_price = product_price
			#print pricelist_disc
			line.pricelist_discount = pricelist_disc

class SaleOrder(models.Model):
	_inherit = "sale.order"
	#TEMP
	def action_button_confirm(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)
		if not context:
			context = {}
		assert len(ids) == 1, 'This option should only be used for a single id at a time.'
		self.signal_workflow(cr, uid, ids, 'order_confirm')

		if context.get('send_email'):
			_logger.info("SHOULD SEND MAIL")
            #self.force_quotation_send(cr, uid, ids, context=context)
		return True


	def _amount_all_wrapper(self, cr, uid, ids, field_name, arg, context=None):

		return self._amount_all(cr, uid, ids, field_name, arg, context=context)
	def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
		cur_obj = self.pool.get('res.currency')
		res = {}
		for order in self.browse(cr, uid, ids, context=context):
			res[order.id] = {
				'amount_untaxed': 0.0,
				'amount_tax': 0.0,
				'amount_total': 0.0,
			}
			val = val1 = 0.0
			cur = order.pricelist_id.currency_id
			for line in order.order_line:
				if line.price_subtotal == 0 or line.price_unit == 0:
					continue
				val1 += line.price_subtotal
				val += self._amount_line_tax(cr, uid, line, context=context)
			res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
			res[order.id]['amount_untaxed'] = cur_obj.round(cr, uid, cur, val1)
			res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
		return res

	discount_method = fields.Selection([('fixed','Fixed'), ('percent','Percent')], string="Discount method")
	order_discount= fields.Float(string="Discount")
	"""
	amount_untaxed = fields.Float(string="Amount discounted", digits=dp.get_precision('Account'),
		store=True, readonly=True, compute='_compute_amount', track_visibility='always')
	amount_tax = fields.Float(string="Amount tax", digits=dp.get_precision('Account'),
		store=True, readonly=True, compute='_compute_amount', track_visibility='always')

	amount_total = fields.Float(string="Total", digits=dp.get_precision('Account'),
		store=True, readonly=True, compute='_compute_amount', track_visibility='always')
	amount_discount = fields.Float(string="Discount", digits=dp.get_precision('Account'),
		store=True, readonly=True, compute='_compute_amount', track_visibility='always')
	discounted = fields.Float(string="Disounted", digits=dp.get_precision("Account"),
		strore=True, readonly=True, compute="_compute_amount", track_visibility="always")
	"""
	amount_discount = fields.Float()
	discounted = fields.Float()
	@api.one
	#@api.depends('order_line.price_subtotal', 'order_line.discount_global', 'order_discount', 'discount_method', 'amount_discount')
	def _compute_amount(self):
		_logger = logging.getLogger(__name__)

		_logger.info("----IN COMPUTE TOTAL AMOUNT")


		self.amount_untaxed = self.currency_id.round(sum(line.full_subtotal for line in self.order_line))
		tax = 0.0
		for line in self.order_line:
			if line.price_unit == 0 or line.price_subtotal == 0:
				continue
			tax += self._amount_line_tax(line, context=None)

		self.amount_tax = tax

		self.discounted = sum(line.price_subtotal for line in self.order_line)
		self.amount_total = self.discounted + self.amount_tax
		self.amount_discount = self.amount_untaxed - self.discounted

	def _prepare_invoice(self, cr, uid, order, lines, context=None):

		#print "PREPARING INVOICE"
		sale_order = self.pool.get('sale.order').browse(cr, uid, order.id, context=None)[0]


		for line in lines:
			for l in sale_order.order_line:

				ln = self.pool.get('account.invoice.line').browse(cr, uid, line, context=None)
				if ln.product_id.id == l.product_id.id and ln.name == l.name and ln.quantity == l.product_uom_qty:
					ln.product_price = l.product_price
					ln.pricelist_discount = l.pricelist_discount
					#print "found", ln.product_price



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
			#TEMP - UNTIL SOL NAME IS FIXED
			name = line.name
			if name and len(name) > 100:
                #_logger.info("-----IS LONG %s" % len(name))
				text = name.split(' ')
				new_name = ''
				for a in text:
					if len(new_name) < 100:
						new_name += '%s ' % a
					name = new_name
			res = {
				'name': name,
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

class StockMove(models.Model):
	_inherit = "stock.move"

	def _create_invoice_line_from_vals(self, cr, uid, move, invoice_line_vals, context=None):
		_logger = logging.getLogger(__name__)
		#start = datetime.now()
		sale_line = move.procurement_id.sale_line_id
		if sale_line:
			invoice_line_vals['product_price'] = sale_line.product_price
			invoice_line_vals['pricelist_discount'] = sale_line.pricelist_discount
		else:
			invoice_line_vals['product_price'] = invoice_line_vals['price_unit']
			invoice_line_vals['pricelist_discount'] = 0.0

		invoice_line_id = super(StockMove, self)._create_invoice_line_from_vals(cr, uid, move, invoice_line_vals, context=context)
		#end = datetime.now()

		#_logger.info("-----------_DURATION CREATE INVOICE LINE STOCK.MOVE %s" % str(end-start))
		return invoice_line_id

	def _get_price_unit_invoice(self, cr, uid, move_line, type, context=None):

	#	_logger = logging.getLogger(__name__)


		if type in ('in_invoice', 'in_refund'):

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

		#_logger = logging.getLogger(__name__)


		res = super(StockMove, self)._get_invoice_line_vals(cr, uid, move, partner, inv_type)

		####

		price_unit, pricelist_discount = self._get_price_unit_invoice(cr, uid, move, inv_type)


		pp = price_unit
		if pricelist_discount > 0:
			pp = (pp * 100) / (100 - pricelist_discount)

		#TEMP - UNTIL SOL NAME IS FIXED
		name = move.name
		if name and len(name) > 100:
                #_logger.info("-----IS LONG %s" % len(name))
				text = name.split(' ')
				new_name = ''
				for a in text:
					if len(new_name) < 100:
						new_name += '%s ' % a
					name = new_name

		res.update({
				'name': name,
				'price_unit': price_unit,
				'pricelist_discount': pricelist_discount,
				'product_price': pp
			})

		return res

class stock_pck_test(models.Model):
	_inherit = "stock.picking"

	def _get_invoice_vals(self, cr, uid, key, inv_type, journal_id, move, context=None):
		_logger = logging.getLogger(__name__)


		res = super(stock_pck_test, self)._get_invoice_vals(cr, uid, key, inv_type, journal_id, move, context=context)
		partner, currency_id, company_id, user_id = key
		discount_method = move.picking_id.sale_id.discount_method or None
		discount = move.picking_id.sale_id.order_discount or 0.0
		sale_id = move.picking_id.sale_id

		user_id = uid
		res.update({
			'user_id': user_id,
			'invoice_discount': discount,
			'discount_method': discount_method,
			'our_bank':partner.our_bank.id if partner.our_bank else None,
			'goods_description_id': sale_id.goods_description_id.id if sale_id else None,
			'carriage_condition_id':sale_id.carriage_condition_id.id if sale_id else None,
			'transportation_reason_id': sale_id.transportation_reason_id.id if sale_id else None,
			'transportation_method_id':sale_id.transportation_method_id.id if sale_id else None,
			'parcels': sale_id.parcels if sale_id else None,
			'partner_bank_id': partner.bank_ids[0].id if partner.bank_ids else None
		})

		return res


	def _invoice_create_line(self, cr, uid, moves, journal_id, inv_type='out_invoice', context=None):
		_logger = logging.getLogger(__name__)

		#start = datetime.now()
		invoice_obj = self.pool.get('account.invoice')
		move_obj = self.pool.get('stock.move')
		invoices = {}
		is_extra_move, extra_move_tax = move_obj._get_moves_taxes(cr, uid, moves, inv_type, context=context)
		product_price_unit = {}
		for move in moves:
			#_logger.info("IN MOVE %s (%s)" % (move.origin, str(datetime.now())))
			company = move.company_id

			origin = move.picking_id.name
			partner, user_id, currency_id = move_obj._get_master_data(cr, uid, move, company, context=context)
			user_id = uid
			key = (partner, currency_id, company.id, user_id)
			#_logger.info("GETTING INVOICE VALS %s (%s)" % (move.origin, str(datetime.now())))
			invoice_vals = self._get_invoice_vals(cr, uid, key, inv_type, journal_id, move, context=context)
			#_logger.info("DONE GETTING INVOICE VALS %s (%s)" % (move.origin, str(datetime.now())))
			if key not in invoices:
				# Get account and payment terms
				#_logger.info("CREATING INVOICE %s (%s)" % (move.origin, str(datetime.now())))
				invoice_id = self._create_invoice_from_picking(cr, uid, move.picking_id, invoice_vals, context=context)
				#_logger.info("DONE CREATING INVOICE %s, %s (%s)" % (move.origin, invoice_id, str(datetime.now())))
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
			#_logger.info("GETTING INVOICE LINE VALS %s (%s)" % (move.origin, str(datetime.now())))
			invoice_line_vals = move_obj._get_invoice_line_vals(cr, uid, move, partner, inv_type, context=dict(context, fp_id=invoice_vals.get('fiscal_position', False)))
			#_logger.info("DONE GETTING INVOICE LINE VALS %s (%s)" % (move.origin, str(datetime.now())))
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
		#	_logger.info("FINAL_CREATING %s (%s)" % (move.origin, str(datetime.now())))
			move_obj._create_invoice_line_from_vals(cr, uid, move, invoice_line_vals, context=context)
			move_obj.write(cr, uid, move.id, {'invoice_state': 'invoiced'}, context=context)
		#	_logger.info("DONE FINAL_CREATING %s (%s)" % (move.origin, str(datetime.now())))

		invoice_obj.button_compute(cr, uid, invoices.values(), context=context, set_total=(inv_type in ('in_invoice', 'in_refund')))
		#end = datetime.now()
		#_logger.info("FINAL_CREATING %s - %s (%s)" % (start, end, end-start))
		return invoices.values()

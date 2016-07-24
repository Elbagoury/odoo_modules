from openerp.osv import fields, osv
import webbrowser
class EbayIds(osv.osv):
	_name = "ebay.ids"

	_columns = {
		'product_id': fields.integer(string="Product ID"),
		'ebay_id': fields.char(string="Ebay_id")
	}
class product_ebay(osv.osv):
	_inherit = "product.template"

	_columns = {
		'copies': fields.char(string="NoOfCopies"),
		'ebay_oem_code': fields.char(string="EbayOEM-obsolete"),
		'with_chip': fields.boolean(string="With chip"),
		'ebay_sync': fields.boolean(string="Sync with ebay"),
		'ebay_id': fields.one2many('ebay.ids', 'product_id', string="Ebay_ids"),
		'ebay_date_added': fields.datetime(string="Added to Ebay"),
		'ebay_price': fields.float(string="Ebay price"),
		'ebay_template_id': fields.many2one('ebay.template'),
		'ebay_item_location': fields.char(string="Ebay postal"),
		'ebay_payment_instruction': fields.text(string="Ebay payment instructions"),
		'ebay_shipping_cost': fields.float(string="Ebay shipping cost"),
		'ebay_additional_item_cost': fields.float(string="Ebay add. shipping cost"),
		'ebay_free_shipping': fields.boolean(string="Ebay free shipping"),
		'ebay_extra_name': fields.char(string="Ebay extra att name"),
		'ebay_extra_value': fields.char(string="Ebay extra att value"),
		'main_name_part': fields.char(string="Ebay main name part"),
		'name_parts': fields.one2many('ebay.name.parts', 'np_id'),
		'stock_limit': fields.integer(default=5, string="Ebay stock limit"),
		'ebay_listing_duration': fields.selection((('Days_7', '7 days'), ('Days_30', '30 days'), ('GTC', 'Good `Till Canceled')), string="Ebay listing duration"),
		'ebay_custom_desc': fields.text(string="Custom description")

	}

	def open_on_ebay(self, cr, uid, ids, context=None):
		#This opens link for product on ebay
		product = self.browse(cr, uid, ids, context=context)
		product = product[0]
		ebay_ids = [x.ebay_id for x in product.ebay_ids]
		if ebay_ids:
			for e in ebay_ids:
				url = 'http://cgi.ebay.it/ws/eBayISAPI.dll?ViewItem&item=%s' % str(e)
				webbrowser.open(url, new=2, autoraise=True)

	def set_price(self, cr, uid, ids, context=None):

		for record in self.browse(cr, uid, ids, context=context):
			ebay_price = record.list_price - 0.1
			record.ebay_price = ebay_price

		return True

	def divide_name(self, cr, uid, ids, context=None):
		current_record = None
		for record in self.browse(cr, uid, ids, context=context):
			current_record = record

		desc = current_record.description

		if len(desc) <= 80:
			return True


		split = desc.split('FOR ')
		main = split[0] + 'FOR '
		rest = ''

		for x in range (1, len(split)):
			rest += split[x]

		others = rest.split(',')

		parts = []
		line = ''

		current_record.main_name_part = main


		for y in range (0, len(others)):
			if (len(line) + len(others[y])) < (80 - len(main)):
				if(len(line) > 0):
					line += ", "
				line += others[y]
				if y == len(others)-1:
					parts.append(line);
			else:
				parts.append(line)
				line = ''

		for p in parts:
			if(p[0] == ' '):
				p = p.replace(p[0], '')


			pro_id = current_record.id
			self.pool.get('ebay.name.parts').create(cr, uid, {'np_id': pro_id, 'name': p})


		return True

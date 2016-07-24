from openerp.osv import fields, osv

class ebay_partner(osv.osv):
	_inherit = "res.partner"

	_columns = {
		"ebay_id": fields.char(string="EbayID"),
		"ebay_orders_count": fields.integer(string="EbayOrderCount")
	}
from openerp.osv import fields, osv

class product_category(osv.osv):
	_inherit = "product.category"
	

	_columns = {
		'ebay_category_id': fields.many2one('ebay.categories.line')
	}

	 
	
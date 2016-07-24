from openerp import fields, models

class product_weights(models.Model):
	_inherit = "product.template"

	weight_fill = fields.Float(string="Fill weight")
	weight_full = fields.Float(string="Full weight")
	weight_empty = fields.Float(string="Empty weight")
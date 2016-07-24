from openerp import fields, models

class color(models.Model):
	_name = 'cartridge.color'

	name = fields.Char(string="Color")

class product_template(models.Model):
	_inherit = "product.template"

	cart_color = fields.Many2one('cartridge.color', string="Cartridge color")
	no_of_copies = fields.Integer(string="Number of pages")

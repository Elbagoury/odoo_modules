from openerp import fields, models

class oem_code(models.Model):
	_inherit = "product.template"

	oem_code = fields.Char(string="OEM code")

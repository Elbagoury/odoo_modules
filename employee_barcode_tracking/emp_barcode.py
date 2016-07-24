from openerp import fields, models

class EmpBarcode(models.Model):
	_inherit = "hr.employee"

	barcode = fields.Char(string="Barcode")
	lv_id = fields.Integer(string="Leave ID")

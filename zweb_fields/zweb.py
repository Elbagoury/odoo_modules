from openerp import fields, models

class zweb_partner(models.Model):
	_inherit = 'res.partner'

	adhoc_id = fields.Char(string="ADHOC ID")
	zw_id = fields.Char(string="ZWeb ID")

	
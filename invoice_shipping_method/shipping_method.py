from openerp import fields, models

class shipping_method(models.Model):
	_inherit = "account.invoice"

	carrier_id = fields.Many2one('delivery.carrier')
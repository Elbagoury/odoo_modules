from openerp import fields, models

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    carrier_id = fields.Many2one('delivery.grid', string="Carrier id")

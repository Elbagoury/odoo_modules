from openerp import models, fields

class PoSoTransferClient(models.Model):
    _inherit = "sale.order"

    remote_document_id = fields.Char(string="Remote document ID")

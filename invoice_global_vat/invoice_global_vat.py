from openerp import models, fields, api
import logging

class InvoiceGlobalVat(models.Model):
    _inherit = "account.invoice"

    @api.one
    def _compute_global_vat(self):
        _logger = logging.getLogger(__name__)
        if not self.invoice_line:
            self.global_vat = 0

        iln = self.invoice_line[0]
        _logger.info("-------------------------- %s " % iln);
        if not iln.invoice_line_tax_id:
            self.global_vat = 0

        tax = iln.invoice_line_tax_id[0]
        _logger.info("-------------------------- %s " % tax)
        self.global_vat = tax.amount * 100


    global_vat = fields.Float(string="Global vat", compute="_compute_global_vat")

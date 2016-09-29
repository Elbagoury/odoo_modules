from openerp import models, fields, api

class InvoiceGlobalVat(models.Model):
    _inherit = "account.invoice"

    @api.one
    def _compute_global_vat(self):
        if not self.invoice_lines:
            return 0

        iln = self.invoice_lines[0]
        if not iln.invoice_line_tax_id:
            return 0

        tax = iln.invoice_line_tax_id[0]
        return tax.amount * 100


    global_vat = fields.Float(string="Global tax %", compute="_compute_global_vat")

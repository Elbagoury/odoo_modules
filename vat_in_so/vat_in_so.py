from openerp import models, fields, api
import logging

class SaleOrder(models.Model):
    _inherit = "sale.order"
    @api.multi
    def _get_vat(self):
        for order in self:
            if order.partner_id:
                order.client_vat = order.partner_id.vat
    client_vat = fields.Char(string="Client VAT", compute="_get_vat")

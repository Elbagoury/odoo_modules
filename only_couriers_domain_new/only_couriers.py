from openerp import fields, models, api

class DeliveryGrid(models.Model):
    _inherit = "delivery.grid"

    is_default = fields.Boolean(string="Default carrier")


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def _get_default_carrier(self):
        
        res = self.pool.get('delivery.grid').search(self._cr, self._uid, [('is_default', '=', True)], context=None)
        if res:
            return res[0]
        return None

    carrier_id = fields.Many2one('delivery.grid', string="Carrier", default=lambda self: self._get_default_carrier())

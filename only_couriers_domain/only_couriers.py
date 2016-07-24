from openerp import fields, models

class DeliveryGrid(models.Model):
    _inherit = "delivery.grid"

    is_default = fields.Boolean(string="Default carrier")

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_default_carrier(self):
        res = self.pool.get('delivery.carrier').search(self._cr, self._uid, [('is_default', '=', True)], context=None)
        if res:
            return res[0]
        return None

    carrier_id = fields.Many2one('delivery.grid', string="Carrier", compute='_get_default_carrier')

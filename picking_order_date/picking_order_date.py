from openerp import fields, models
import logging

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_order_line_procurement(self, cr, uid, order, line, group_id=False, context=None):
        _logger = logging.getLogger(__name__)
        res = super(SaleOrder, self)._prepare_order_line_procurement(cr, uid, order, line, group_id=group_id, context=context)
        res.update({
            'origin_date': order.date_order
        })
        _logger.info("-----------CREATING PICKING %s" % res)
        return res

class StockPicking(models.Model):
    _inherit = "stock.picking"

    origin_date = fields.Datetime(string="Origin document date")

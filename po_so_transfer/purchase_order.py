from openerp import models, fields
import logging

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    remote_order_id = fields.Integer(string="Remote order ID")
    transfer_remotely = fields.Boolean(string="Transfer remotely")

    def transfer_ord(self, cr, uid, ids, context=None):
        _logger = logging.getLogger(__name__)

        _logger.info("------------------------ISII")

        self.pool.get('po.so.transfer').transfer(cr, uid, ids, context=context)

    def wkf_confirm_order(self, cr, uid, ids, context=None):
        _logger = logging.getLogger(__name__)

        _logger.info("------------------------ISII")
        super(PurchaseOrder, self).wkf_confirm_order(cr, uid, ids, context=None)
        order = self.browse(cr, uid, ids, context=None)
        _logger.info(order)
        for o in order:
            _logger.info(o)
            if o.transfer_remotely:
                o.transfer_ord()

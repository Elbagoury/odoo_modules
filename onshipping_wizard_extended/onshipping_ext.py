from openerp.osv import fields, osv
import datetime

class OnShippingExtended(osv.osv_memory):
    _inherit = "stock.invoice.onshipping"
    def _get_today(self, cr, uid, context=None):
        return datetime.datetime.now()
    _columns = {
        'invoice_date': fields.date('Invoice Date')
    }

    _defaults = {
        'invoice_date': _get_today
    }

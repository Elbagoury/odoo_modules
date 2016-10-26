from openerp import fields, models, api

class SaleOrder(models.Model):
    _inherit = "sale.order"

    state = fields.Selection([
            ('draft', 'Draft Quotation'),
            ('preorder', 'Preorder'),
            ('sent', 'Quotation Sent'),
            ('cancel', 'Cancelled'),
            ('waiting_date', 'Waiting Schedule'),
            ('progress', 'Sales Order'),
            ('manual', 'Sale to Invoice'),
            ('shipping_except', 'Shipping Exception'),
            ('invoice_except', 'Invoice Exception'),
            ('done', 'Done'),
            ], string='Status', readonly=True, copy=False, help="Gives the status of the quotation or sales order.\
              \nThe exception status is automatically set when a cancel operation occurs \
              in the invoice validation (Invoice Exception) or in the picking list process (Shipping Exception).\nThe 'Waiting Schedule' status is set when the invoice is confirmed\
               but waiting for the scheduler to run on the order date.", select=True)

    def set_preorder(self, cr, uid, ids, context=None):
        for o in self.browse(cr, uid, ids, context=None):
            for ol in o.order_line:
                ol.state = 'preorder'
            o.state = 'preorder'

    def set_draft(self, cr, uid, ids, context=None):
        for o in self.browse(cr, uid, ids, context=None):
            for ol in o.order_line:
                ol.state = 'draft'
            o.state = 'draft'



class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    state = fields.Selection([('cancel', 'Cancelled'),('draft', 'Draft'), ('preorder', 'Preorder'),('confirmed', 'Confirmed'),('exception', 'Exception'),('done', 'Done')],
    'Status', required=True, readonly=True, copy=False,
    help='* The \'Draft\' status is set when the related sales order in draft status. \
        \n* The \'Confirmed\' status is set when the related sales order is confirmed. \
        \n* The \'Exception\' status is set when the related sales order is set as exception. \
        \n* The \'Done\' status is set when the sales order line has been picked. \
        \n* The \'Cancelled\' status is set when a user cancel the sales order related.')

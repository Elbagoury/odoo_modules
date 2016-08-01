from openerp import models, fields, api, _
from openerp.osv import osv

class CreateHelpRequest(models.TransientModel):
    _name = "create.help.request"

    def _get_sale_order(self):

        return self._context.get('active_ids')[0]
    query = fields.Char(string="Request name (query)", required=True)
    sale_order = fields.Many2one('sale.order', string="Sale order", default=_get_sale_order)

    def create_request(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids, context=context)
        order = wizard.sale_order
        if not order:
            raise osv.except_osv(_("Create help request"), _("No sale order selected"))
        if not order.partner_id:
            raise osv.except_osv(_("Create help request"), _("Sale order selected has no partner"))
        vals = {
            'name': wizard.query,
            'user_id': uid,
            'partner_id': order.partner_id.id,
            'ref': 'sale.order,%s' % order.id,
            'phonenumber': order.partner_id.phone or '',
            'email_from': order.partner_id.email

        }
        res = self.pool.get('crm.helpdesk').create(cr, uid, vals, context=None)
        return {'type': 'ir.actions.act_window_close'}


class crm_helpdesk_extended(models.Model):
    _inherit = 'crm.helpdesk'
    state = fields.Selection([('draft', 'New'),
     ('open', 'Managed'),
     ('pending', 'Pending'),
     ('done', 'Closed'),
     ('cancel', 'Back Order Cancelled')], 'Status', readonly=True, track_visibility='onchange',
                      help='The status is set to \'Draft\', when a case is created.\
                      \nIf the case is in progress the status is set to \'Open\'.\
                      \nWhen the case is over, the status is set to \'Done\'.\
                      \nIf the case needs to be reviewed then the status is set to \'Pending\'.')
    phonenumber = fields.Char(string="Phone number")

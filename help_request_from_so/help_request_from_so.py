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
    state = fields.Selection([('draft', 'Warehouse'),
     ('time_preview', 'Time previewing'),
     ('open', 'Production check'),
     ('sales_call', 'Sales call'),
     ('pending', 'Waiting for customer'),
     ('complete_info', 'Complete info'),
     ('done', 'Closed')], 'Status', readonly=True, track_visibility='onchange',
                      help='The status is set to \'Draft\', when a case is created.\
                      \nIf the case is in progress the status is set to \'Open\'.\
                      \nWhen the case is over, the status is set to \'Done\'.\
                      \nIf the case needs to be reviewed then the status is set to \'Pending\'.')
    phonenumber = fields.Char(string="Phone number")


class SaleOrder(models.Model):
  _inherit = "sale.order"

  @api.multi
  def _get_helpdesk(self):
    for order in self:
        helpdesk_obj = self.pool.get('crm.helpdesk')
        key = "sale.order,%s" % order.id
        helpdesks = helpdesk_obj.search(self._cr, self._uid, [('ref', '=', key)], context=None)
        if helpdesks:
          hdid = helpdesks[0]
          helpdesk = helpdesk_obj.browse(self._cr, self._uid, hdid, context=None)
          if helpdesk:
            order.helpdesk_note = helpdesk.name
            order.helpdesk_state = helpdesk.state

    
  helpdesk_note = fields.Char(string="Helpdesk note", compute="_get_helpdesk")
  helpdesk_state = fields.Char(string="Helpdesk state", compute="_get_helpdesk")

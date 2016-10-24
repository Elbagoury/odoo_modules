from openerp import models, fields, api, _
from openerp.osv import osv
import logging

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
            'section_id': order.partner_id.section_id.id if order.partner_id.section_id else None,
            'ref': 'sale.order,%s' % order.id,
            'phonenumber': order.partner_id.phone or '',
            'email_from': order.partner_id.email

        }
        res = self.pool.get('crm.helpdesk').create(cr, uid, vals, context=None)
        return {'type': 'ir.actions.act_window_close'}


class crm_helpdesk_extended(models.Model):
    _inherit = 'crm.helpdesk'


    @api.multi
    def _get_desc(self):
        _logger = logging.getLogger(__name__)
        for item in self:
            if not item.ref:
                return None

            _logger.info("--HAS SO: %s" % item.ref.name)
            if item.ref and item.ref.order_line:
                _logger.info("--HAS SO LINES: %s" % len(item.ref.order_line))
                text = "<table border='1'>"
                text += "<tr><td>Code</td><td>Description</td><td>Qty</td><td><td>Price</td><td>Subtotal</td></tr>"

                for line in item.ref.order_line:
                    text += "<tr>"
                    text += "<td style='padding-right: 10px;'>%s</td><td style='padding-right: 30px;'>%s</td><td style='padding-right: 3px;'>%s</td><td style='padding-right: 20px;'>%s</td><td style='padding-right: 20px;'>%s</td><td style='padding-right: 20px;'>%s</td>" % (line.product_id.name, line.name, line.product_uom_qty, line.product_uom.name, line.price_unit,line.price_subtotal)
                    text += "</tr>"

                text += "</table>"

                text += "<table border='1' style='margin:10px;margin-left:0px'><tr><td style='padding-right: 10px;'>Without taxes: <b>%s</b></td><td style='padding-right: 10px;'>Taxes: <b>%s</b></td><td style='padding-right: 10px;'>Total: <b>%s</b></td></tr></table>" % (item.ref.amount_untaxed, item.ref.amount_tax, item.ref.amount_total)
                item.order = text


    state = fields.Selection([('draft', 'Warehouse/Production'),
     ('inkjet', "Inkjet"),
     ('spare_parts', "Spare parts"),
     ('sales_call', 'Sales call'),
     ('pending', 'Answer from client'),
     ('complete_info', 'Informations complete'),
     ('done', 'Closed')], 'Status', readonly=True, track_visibility='onchange',
                      help='The status is set to \'Draft\', when a case is created.\
                      \nIf the case is in progress the status is set to \'Open\'.\
                      \nWhen the case is over, the status is set to \'Done\'.\
                      \nIf the case needs to be reviewed then the status is set to \'Pending\'.')
    phonenumber = fields.Char(string="Phone number")
    order = fields.Html(string="AddNote", compute="_get_desc")

    def on_change_partner_id(self, cr, uid, ids, partner_id, context=None):
        values = {}
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            values = {
                'email_from': partner.email,
                'section_id': partner.section_id.id if partner.section_id else None
            }
        return {'value': values}

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
  helpdesk_state = fields.Selection([('draft', 'Warehouse/Production'),
     ('inkjet', "Inkjet"),
     ('spare_parts', "Spare parts"),
     ('sales_call', 'Sales call'),
     ('pending', 'Answer from client'),
     ('complete_info', 'Informations complete'),
     ('done', 'Closed')], string="Helpdesk state", compute="_get_helpdesk")

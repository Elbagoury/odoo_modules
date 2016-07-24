from openerp import fields, models, api, _

class ClientNoteOnOrder(models.Model):
    _inherit = "sale.order"

    box_note = fields.Text(string="Note for box")

    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        res = super(ClientNoteOnOrder, self).onchange_partner_id(cr, uid, ids, part, context=context)
        partner = self.pool.get('res.partner').browse(cr, uid, part, context=None)
        if partner:
            partner = partner[0]
            res['value'].update({
                'box_note': partner.comment or ''
                })
        return res

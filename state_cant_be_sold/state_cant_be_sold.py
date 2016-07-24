from openerp import fields, models, api, _
from openerp.osv import osv

class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.onchange('state')
    def onchange_state(self):

        if self.state not in ['sellable', 'end']:
            self.sale_ok = False
        else:
            self.sale_ok = True

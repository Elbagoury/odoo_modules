from openerp import fields, models
import openerp.addons.decimal_precision as dp

class DeliveryGrid(models.Model):
    _inherit = "delivery.grid.line"

    list_price = fields.Float(string="List price", digits=dp.get_precision('Delivery'))
    #new_price = fields.Float(string="New one", digits=dp.get_precision('Delivery'))

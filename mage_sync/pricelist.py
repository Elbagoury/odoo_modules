from openerp import models, fields

class Pricelist_magneto(models.Model):
    _inherit = 'product.pricelist'
    sync_with_magento = fields.Boolean()
    mage_cat = fields.Integer()
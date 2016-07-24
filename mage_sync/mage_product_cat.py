from openerp import models, fields

class Magneto_product_category(models.Model):
    _inherit = 'product.category'
    
    do_not_publish_mage = fields.Boolean(string="Do not publish on magento")
    mage_root = fields.Boolean(string="Root on magento")

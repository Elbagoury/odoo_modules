from openerp import fields, models

class AmazonPrice(models.Model):
    _inherit = "product.template"

    amazon_price = fields.Float(string="Amazon price")

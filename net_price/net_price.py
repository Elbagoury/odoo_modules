from openerp import fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    net_price = fields.Float(string="Net price")

class ProductProduct(models.Model):
    _inherit = "product.product"

    net_price = fields.Float(string="Net price")

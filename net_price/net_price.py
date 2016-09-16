from openerp import fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    net_price = fields.Float(string="Net price")

class ProductProduct(models.Model):
    _inherit = "product.product"

    net_price = fields.Float(string="Net price")

    def create(self, cr, uid, vals, context=None):
        if 'product_tmpl_id' in vals:
            template = self.pool.get('product.template').browse(cr, uid, vals['product_tmpl_id'], context=None)
            vals.update(
                {
                    'net_price': template.net_price or 0.0
                }
            )
        res = super(ProductProduct, self).create(cr, uid, vals, context=None)
        return res

    def update_prices(self, cr, uid, ids, context=None):
        product_ids = self.pool.get('product.product').search(cr, uid, [('active', '=', True), ('product_tmpl_id', '!=', False)], context=None)
        products = self.pool.get('product.product').browse(cr, uid, product_ids, context=None)

        for p in products:
            p.net_price = p.product_tmpl_id.net_price or 0.0

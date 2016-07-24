from openerp import fields, models, api

class product_supplierinfo_extended(models.Model):
    _inherit = "product.supplierinfo"

    currency_id = fields.Many2one('res.currency', string="Currency")

    @api.onchange('name')
    def insert_pricelist(self):

        if self.name:
            partner = self.name
        else:
            return None

        if partner.property_product_pricelist_purchase:
            self.currency_id = partner.property_product_pricelist_purchase.currency_id.id


        return None

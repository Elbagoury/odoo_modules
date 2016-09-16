from openerp import fields, models, api, _
import logging

class ResPartner(models.Model):
    _inherit = "res.partner"

    value_ids = fields.Many2many('product.attribute.value', string="Values for client")


class ResCompany(models.Model):
    _inherit = "res.company"

    value_ids = fields.Many2many('product.attribute.value', string="Default value id")

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    @api.onchange('product_template')
    def onchange_product_template(self):
        #_logger = logging.getLogger(__name__)
        super(SaleOrderLine, self).onchange_product_template(self)
        item = self
        if True:
            partner = item.order_id.partner_id if item.order_id else None
            product_template = item.product_template
            products = product_template.product_variant_ids
            company = self.pool.get('res.company').browse(cr, uid, 1, context=None)
            defaults = [x.id for x in company.value_ids] if company.value_ids else []
            if not partner:
                return None

            if not partner.value_ids and not defaults:
                return None

            values = [x.id for x in partner.value_ids]
            #_logger.info("=%s, %s" % (partner.name, values))
            for product in products:
                if not product.attribute_value_ids:
                    continue
                #_logger.info("-2-- %s" % product.attribute_value_ids)
                if any(x.id in values for x in product.attribute_value_ids):
                    #_logger.info("-3-- %s, %s product_FOUND: " % (product.name, product.id))
                    self.product_id = product.id
                if not self.product_id and defaults:
                    if any(x.id in defaults for x in product.attribute_value_ids):
                        self.product_id = product.id

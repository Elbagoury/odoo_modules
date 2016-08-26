from openerp import fields, models, api, _
import logging
class ResPartner(models.Model):
    _inherit = "res.partner"

    pricelist_summary_product_id = fields.Many2one('product.template', string="Product to check")
    pricelist_summary = fields.Text(string="Prices for selected product")

    def get_prices(self, cr, uid, ids, context=None):
        partner = self.browse(cr, uid, ids, context=None)
        if not partner.pricelist_summary_product_id or not partner.property_product_pricelist:
            return True
        product = partner.pricelist_summary_product_id
        pricelist = partner.property_product_pricelist
        if True:

            text = ''
            text += "FULL PRICE: %s\n" % product.list_price
            if product.net_price:
                text+= "Net price: %s\n" % product.net_price
            categ_ids = self.pool.get('sale.order.line')._get_categ_ids(product.categ_id) or []
            if pricelist:
                if not pricelist.version_id:
                    return True
                version = pricelist.version_id[0]
                items = version.items_id

                for i in items:

                    if i.product_tmpl_id:
                        if i.product_tmpl_id == product.id:
                            text += "- Min. qty: %s - Price: %s\n" % (i.min_quantity, (1+i.price_discount) * product.list_price + i.price_surcharge)
                    elif i.categ_id:
                        if i.categ_id.id in categ_ids:
                            text += "- Min. qty: %s - Price: %s\n" % (i.min_quantity, (1+i.price_discount) * product.list_price + i.price_surcharge)
                    else:
                        text += "- Min. qty: %s - Price: %s\n" % (i.min_quantity, (1+i.price_discount) * product.list_price + i.price_surcharge)
            partner.pricelist_summary = text

class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    is_main = fields.Boolean(string="Include in product pricelist summary")
class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.one
    def _get_pricelist_discounts(self):
        cr = self._cr
        uid = self._uid
        pricelist_ids = self.pool.get('product.pricelist').search(cr, uid, [('is_main', '=', True)], context=None)
        pricelists = self.pool.get('product.pricelist').browse(cr, uid, pricelist_ids, context=None)
        if True:
            product = self
            text = ''
            text += "FULL PRICE: %s\n" % product.list_price
            if product.net_price:
                text+= "Net price: %s\n" % product.net_price
            categ_ids = self.pool.get('sale.order.line')._get_categ_ids(product.categ_id) or []
            for pricelist in pricelists:
                if not pricelist.version_id:
                    continue
                version = pricelist.version_id[0]
                items = version.items_id
                text += "%s:\n" % pricelist.name
                for i in items:

                    if i.product_tmpl_id:
                        if i.product_tmpl_id == product.id:
                            text += "- Min. qty: %s - Price: %s\n" % (i.min_quantity, (1+i.price_discount) * product.list_price + i.price_surcharge)
                    elif i.categ_id:
                        if i.categ_id.id in categ_ids:
                            text += "- Min. qty: %s - Price: %s\n" % (i.min_quantity, (1+i.price_discount) * product.list_price + i.price_surcharge)
                    else:
                        text += "- Min. qty: %s - Price: %s\n" % (i.min_quantity, (1+i.price_discount) * product.list_price + i.price_surcharge)
            product.pricelist_discount_summary = text

    pricelist_discount_summary = fields.Text(string="Pricelist discount summary", compute="_get_pricelist_discounts")



class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    pricelist_discount_summary = fields.Text(string="Pricelist discount summary")

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):

            _logger = logging.getLogger(__name__)
            _logger.info("IN SUMMARY")
            res = super(SaleOrderLine, self).product_id_change(cr, uid, ids, pricelist, product, qty=qty,
                    uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
                    lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, context=None)


            pls = self.pool.get('product.pricelist').browse(cr, uid, [pricelist], context=None)[0]
            product = self.pool.get('product.product').browse(cr, uid,[product], context=None)
            if not product:
                return res
            print pls.name
            r2 = []
            version = pls.version_id[0]
            items = version.items_id
            text = ''

            categ_ids = self._get_categ_ids(product.categ_id) or []


            for i in items:

                if i.product_id:
                    if i.product_id == product.id:
                        text += "- Min. qty: %s - Price: %s\n" % (i.min_quantity, (1+i.price_discount) * product.list_price + i.price_surcharge)
                elif i.categ_id:
                    if i.categ_id.id in categ_ids:
                        text += "- Min. qty: %s - Price: %s\n" % (i.min_quantity, (1+i.price_discount) * product.list_price + i.price_surcharge)
                else:
                    text += "- Min. qty: %s - Price: %s\n" % (i.min_quantity, (1+i.price_discount) * product.list_price + i.price_surcharge)

            if product.net_price or product.product_tmpl_id.net_price:
                price = str(product.net_price) if product.net_price > 0 else str(product.product_tmpl_id.net_price)
                text += "- Net price: %s" % price
            res['value'].update({
                'pricelist_discount_summary': text,

            })
            return res
    def _get_categ_ids(self, categ):
            categ_ids = {}
            while categ:
                categ_ids[categ.id] = True
                categ = categ.parent_id
            categ_ids = categ_ids.keys()
            return categ_ids

from openerp import fields, models, api, _
import logging

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    pricelist_discount_summary = fields.Text(string="Pricelist discont summary")

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

            categ_ids = _get_categ_ids(product.categ_id) or []


            for i in items:

                if i.product_id and i.product_id == product.id:
                    text += "- Min. qty: %s - Price: %s\n" % (i.min_quantity, (1+i.price_discount) * product.list_price + i.price_surcharge)
                elif i.categ_id and i.categ_id in categ_ids:
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
def _get_categ_ids(categ):

    categ_ids = {}
    while categ:
        categ_ids[categ.id] = True
        categ = categ.parent_id
    categ_ids = categ_ids.keys()
    return categ_ids

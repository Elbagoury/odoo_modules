from openerp import fields, models, api, _
import logging
from datetime import datetime
import xmlrpclib

class InternalOrders(models.Model):
    _name = "internal.moves"

    ro_url = fields.Char(string="Remote url")
    ro_db = fields.Char(string="Remote db")
    ro_user = fields.Char(string="Remote user")
    ro_pass = fields.Char(string="Remote pass")
    ro_port = fields.Char(string="Remote port")
    in_use = fields.Boolean(string="Use this remote")
    default_value_for_variants = fields.Many2one('product.attribute.value', string="Default value for variant")

    def transfer(self, cr, uid, order_id, context=None):
        _logger = logging.getLogger(__name__)
        def_id = self.search(cr, uid, [("in_use", '=', True)], context=None)
        if not def_id:
            return None

        record = self.browse(cr, uid, def_id, context=None)

        url = record.ro_url
        db = record.ro_db
        username = record.ro_user
        password = record.ro_pass

        common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
        uidx = common.authenticate(db, username, password, {})

        models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(url))

        order = self.pool.get('sale.order').browse(cr, uidx, order_id, context=None)[0]
        _logger.info("++++++ %s" % order.name)
        par = models.execute_kw(db, uid, password,
        	'res.partner', 'read', [[190856]], {'fields':['property_product_pricelist']}) #make user insertable

        par = par[0]
        pricelist = par['property_product_pricelist'][0] if par['property_product_pricelist'] else 1
        vals = {
            'partner_id': 190856,
            'location_id': 1,
            'pricelist_id': pricelist
        }

        po = models.execute_kw(db, uidx, password,
            'purchase.order', 'create', [vals])

        for line in order.order_line:
            remote_product_id = models.execute_kw(db, uidx, password,
                'product.product', 'search_read', [[['default_code', '=', line.product_id.default_code]]], {'fields': ['uom_id']})
            remote_uom = models.execute_kw(db, uidx, password,
                'product.uom', 'search', [[['name', '=', remote_product_id[0]['uom_id'][1]]]])

            vals = {
                'product_id': remote_product_id[0]['id'],
                'name': line.name,
                'product_uom': remote_uom[0] if len(remote_uom) else 1,
                'product_qty': line.product_uom_qty,
                'date_planned': datetime.now().strftime('%d/%m/%Y'),
                'price_unit': line.price_unit,
                'order_id': po,
                'taxes_id': [[6, False, [x.id for x in line.tax_id]]]
            }
            models.execute_kw(db, uidx, password,
                'purchase.order.line', 'create', [vals])

        order.remote_order_id = po

class SaleOrder(models.Model):
    _inherit = "sale.order"


    remote_order_id = fields.Integer(string="Remote Order ID")
    transfer_remotely = fields.Boolean(string="Transfer remotely", default="True")

    def action_button_confirm(self, cr, uid, ids, context=None):
        super(SaleOrder, self).action_button_confirm(cr, uid, ids, context=None)
        order = self.browse(cr, uid, ids, context=None)
        for o in order:
            if o.transfer_remotely:
                o.transfer_order()


    def transfer_order(self, cr, uid, ids, context=None):
        self.pool.get('internal.moves').transfer(cr, uid, ids, context=None)

from openerp import fields, models, api, _
import logging
from datetime import datetime
import xmlrpclib

class PoSoTransfer(models.Model):
    _name = "po.so.transfer"

    ro_url = fields.Char(string="Remote url")
    ro_db = fields.Char(string="Remote db")
    ro_user = fields.Char(string="Remote user")
    ro_pass = fields.Char(string="Remote pass")
    ro_port = fields.Char(string="Remote port")
    in_use = fields.Boolean(string="Use this remote")
    default_value_for_variants = fields.Many2one('product.attribute.value', string="Default value for variant")
    remote_partner_id = fields.Char(string="Remote partner ID")

    def transfer(self, cr, uid, order_id, context=None):
        _logger = logging.getLogger(__name__)
        _logger.info("IN TRANSFER ORDER")
        def_id = self.search(cr, uid, [("in_use", '=', True)], context=None)
        if not def_id:
            _logger.info("no configs in use")
            return None

        record = self.browse(cr, uid, def_id, context=None)

        url = record.ro_url
        db = record.ro_db
        username = record.ro_user
        password = record.ro_pass
        partner_foreign_id = int(record.remote_partner_id) if record.remote_partner_id else 0

        common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
        uidx = common.authenticate(db, username, password, {})

        models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(url))

        order = self.pool.get('purchase.order').browse(cr, uidx, order_id, context=None)[0]

        par = models.execute_kw(db, uidx, password,
        	'res.partner', 'read', [[partner_foreign_id]], {'fields':['property_product_pricelist']}) #make user insertable

        par = par[0]
        pricelist = par['property_product_pricelist'][0] if par['property_product_pricelist'] else 1
        vals = {
            'partner_id': partner_foreign_id,
            'pricelist_id': pricelist,
            'partner_invoice_id': partner_foreign_id,
            'partner_shipping_id': partner_foreign_id,
            'order_policy': 'picking',
            'picking_policy': 'direct',
            'warehouse_id': 1,
            'remote_document_id': order.name
        }

        so = models.execute_kw(db, uidx, password,
            'sale.order', 'create', [vals])

        for line in order.order_line:
            remote_product_id = models.execute_kw(db, uidx, password,
                'product.product', 'search_read', [[['default_code', '=', line.product_id.default_code]]], {'fields': ['uom_id', 'product_tmpl_id']})

            vals = {
                "product_uos_qty": line.product_qty,
                "product_uom_qty": line.product_qty,
                "order_partner_id": partner_foreign_id,
                "product_template": remote_product_id[0]['product_tmpl_id'][0],
                "delay": 0,
                'product_id': remote_product_id[0]['id'],
                'name': line.name,
                'product_uom': remote_product_id[0]['uom_id'][0] if 'uom_id' in remote_product_id[0] else 1,
                'price_unit': line.price_unit,
                'order_id': so,
                'tax_id': [[6, False, [x.id for x in line.taxes_id]]]
            }
            models.execute_kw(db, uidx, password,
                'sale.order.line', 'create', [vals])

        order.remote_order_id = so
"""
class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    remote_order_id = fields.Integer(string="Remote Order ID")
    transfer_remotely = fields.Boolean(string="Transfer remotely", default="True")

    def action_confirm(self, cr, uid, ids, context=None):
        super(PurchaseOrder, self).action_confirm(cr, uid, ids, context=None)
        order = self.browse(cr, uid, ids, context=None)
        for o in order:
            if o.transfer_remotely:
                o.transfer_order()

    def transfer_order(self, cr, uid, ids, context=None):
        _logger = logging.getLogger(__name__)
        x_logger.info("I---------------N Transfer order")
        self.pool.get('po.so.transfer').transfer(cr, uid, ids, context=None)
"""

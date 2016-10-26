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
    po_client_id  = fields.Integer(string="Client (supplier) to be used for PO")
    remote_client_id = fields.Integer(string="Remote client ID")

    def transfer(self, cr, uid, order_id, context=None):
        _logger = logging.getLogger(__name__)
        def_id = self.search(cr, uid, [("in_use", '=', True)], context=None)
        if not def_id:
            return None

        record = self.browse(cr, uid, def_id, context=None)

        order = self.pool.get('sale.order').browse(cr, uid, order_id, context=None)[0]
        _logger.info("++++++ %s" % order.name)

        #CREATE PO local
        po_client = record.po_client_id

        vals = {
            'partner_id': po_client,
            'location_id': 1,
            'pricelist_id': order.pricelist_id.id
        }

        po_local_id = self.pool.get('purchase.order').create(cr, uid, vals, context=None)

        for line in order.order_line:
            vals = {
                'product_id': line.product_id.id,
                'name': line.name,
                'product_qty': line.product_uom_qty,
                'date_planned': datetime.now().strftime('%d/%m/%Y'),
                'price_unit': line.price_unit,
                'order_id': po_local_id,
                'taxes_id': [[6, False, [x.id for x in line.tax_id]]]
            }
            line_id = self.pool.get('purchase.order.line').create(cr, uid, vals, context=None)


        #CREATE REMOTE SO
        url = record.ro_url
        db = record.ro_db
        username = record.ro_user
        password = record.ro_pass

        common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
        uidx = common.authenticate(db, username, password, {})

        models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(url))


        par = models.execute_kw(db, uid, password,
        	'res.partner', 'read', [[190856]], {'fields':['property_product_pricelist']}) #make user insertable

        par = par[0]
        pricelist = par['property_product_pricelist'][0] if par['property_product_pricelist'] else 1
        vals = {
            'partner_id': record.remote_client_id,
            'pricelist_id': pricelist,
            'partner_invoice_id': record.remote_client_id,
            'partner_shipping_id': record.remote_client_id,
            'order_policy': 'picking',
            'picking_policy': 'direct',
            'warehouse_id': 1,
            'remote_document_id': order.name,
            'state': 'preorder'
        }

        so = models.execute_kw(db, uidx, password,
            'sale.order', 'create', [vals])

        for line in order.order_line:
            remote_product_id = models.execute_kw(db, uidx, password,
                'product.product', 'search_read', [[['default_code', '=', line.product_id.default_code]]], {'fields': ['uom_id', 'product_tmpl_id']})

            vals = {
                "product_uos_qty": line.product_uos_qty,
                "product_uom_qty": line.product_uom_qty,
                "order_partner_id": record.remote_client_id,
                "product_template": remote_product_id[0]['product_tmpl_id'][0],
                "delay": 0,
                'product_id': remote_product_id[0]['id'],
                'name': line.name,
                'product_uom': remote_product_id[0]['uom_id'][0] if 'uom_id' in remote_product_id[0] else 1,
                'price_unit': line.price_unit,
                'order_id': so,
                'tax_id': [[6, False, [x.id for x in line.tax_id]]],
                'state': 'preorder'
            }
            models.execute_kw(db, uidx, password,
                'sale.order.line', 'create', [vals])
        #order.remote_order_id = po

class SaleOrder(models.Model):
    _inherit = "sale.order"


    remote_order_id = fields.Integer(string="Remote Order ID")
    transfer_remotely = fields.Boolean(string="Transfer remotely", default="True")
    """
    def action_button_confirm(self, cr, uid, ids, context=None):
        super(SaleOrder, self).action_button_confirm(cr, uid, ids, context=None)
        order = self.browse(cr, uid, ids, context=None)
        for o in order:
            if o.transfer_remotely:
                o.transfer_order()
    """
    def transfer_order(self, cr, uid, ids, context=None):
        self.pool.get('internal.moves').transfer(cr, uid, ids, context=None)

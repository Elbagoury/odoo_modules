from openerp import fields, models, api, _
from openerp.osv import osv
from openerp import SUPERUSER_ID
import logging
from datetime import time



class SaleOrderLine(models.Model):
	_inherit = "sale.order.line"

	def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
			uom=False, qty_uos=0, uos=False, name='', partner_id=False,
			lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
            _logger = logging.getLogger(__name__)
            res = super(SaleOrderLine, self).product_id_change(cr, uid, ids, pricelist, product, qty=qty,
                    uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
                    lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, context=None)
            product_obj = self.pool.get('product.product')
            product_obj = product_obj.browse(cr, uid, product, context=None)
            name = product_obj.description or product_obj.name
            if name and len(name) > 100:
                _logger.info("-----IS LONG %s" % len(name))
                text = name.split(' ')
            	new_name = ''
            	for a in text:
            		if len(new_name) < 100:
            			new_name += '%s ' % a
                name = new_name
                if product_obj.oem_code:
                    name += " - OEM: %s" % product_obj.oem_code
                if product_obj.no_of_copies:
                    name += " - Copies: %s" % product_obj.no_of_copies
                #_logger.info(name)
            value = res.setdefault('value', {})

            value['name'] = name

            return res


class AccountInvoiceLine(models.Model):
	_inherit = "account.invoice.line"

	@api.multi
	def product_id_change(self, product, uom_id, qty=0, name='', type='out_invoice',
			partner_id=False, fposition_id=False, price_unit=False, currency_id=False,
			company_id=None):
            res = super(AccountInvoiceLine, self).product_id_change(product, uom_id, qty=qty, name=name, type=type,
    			     partner_id=partner_id, fposition_id=fposition_id, price_unit=price_unit, currency_id=currency_id,
    			              company_id=company_id)

            product_obj = self.pool.get('product.product').browse(self._cr, self._uid, product)
            name = product_obj.description or product_obj.name
            if name and len(name) > 100:
                text = name.split(' ')
            	new_name = ''
            	for a in text:
            		if len(new_name) < 100:
            			new_name += '%s ' % a
                name = new_name
            res['value'].update({
                'name': name
            })
            return res

from openerp import models, fields, api, _
import logging
from openerp.exceptions import except_orm, Warning, RedirectWarning
from magento_api import MagentoAPI

class magento_so(models.Model):
	_inherit = 'sale.order'

	magento_id = fields.Char(string="MagentoID")

	def manual_invoice(self, cr, uid, ids, context=None):
		res = super(magento_so, self).manual_invoice(cr, uid, ids, context=None)
		return res
		#EXPORT OF INVOICE TO MAGENTO REQUERES MORE WORK
		magento_id = list(s.magento_id for s in self.browse(cr, uid, ids, context))[0]
		if magento_id:

			inv_obj = self.pool.get('account.invoice').browse(cr, uid, res['res_id'], context)[0]
			items = []
			for item in self.browse(cr, uid, ids, context):
				for i in item.order_line:

					items.append({"qty": '1', "order_item_id":'65'})#str(int(i.product_uom_qty))})

			if items:
				for record in self.pool.get('magento_sync').browse(cr, uid, 1, context=context):
					r = record

				cs = {
					'location': r.mage_location,
					'port': r.mage_port,
					'user': r.mage_user,
					'pwd': r.mage_pwd
				}
				inv_obj.magento_id = self.pool.get('magento_sync').export_invoice(magento_id, [{'qty':'1', 'order_item_id':'65'}], cs)
				if not inv_obj.magento_id:
					raise except_orm("MAGENTO CONNECTOR", "INVOICE COULD NOT BE EXPORTED TO MAGENTO STORE")

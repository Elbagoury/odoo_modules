from openerp import models, fields
from magento_api import MagentoAPI

class Customer_magneto(models.Model):
	_inherit = 'res.partner'

	magento_id = fields.Integer(string="MagentoID")
	magento_address_id = fields.Integer(string="MagentoAddressItemID")
	sync_to_mage = fields.Boolean(default=True, string="Sync_to_mage")
	last_name = fields.Char(string="Last name")
	mage_customer_pass = fields.Char(string="Password for magento")

	def export_cust_immediately(self, cr, uid, ids, context=None):
		mids = self.pool.get('magento_sync').search(cr, uid, [], context=None)
		mid = mids[0]
		return self.pool.get('magento_sync').export_customers(cr, uid, mid, context=None, client_id=ids[0])

		

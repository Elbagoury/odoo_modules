from openerp import models, fields
import logging

class Magneto_product_category(models.Model):
    _inherit = 'product.category'

    do_not_publish_mage = fields.Boolean(string="Do not publish on magento")
    mage_root = fields.Boolean(string="Root on magento")

    def export_pros_in_cat(self, cr, uid, ids, context=None):
        _logger = logging.getLogger(__name__)
        product_ids = self.pool.get('product.template').search(cr, uid, [("categ_id.id", 'in', ids)], context=None)

        record_ids = self.pool.get('magento_sync').search(cr, uid, [], context=None)[0]
        r = self.pool.get('magento_sync').browse(cr, uid, record_ids, context=None)
        cs = {
            'location': r.mage_location,
            'port': r.mage_port,
            'user': r.mage_user,
            'pwd': r.mage_pwd
        }
        _logger.info('----- Export from category: %s' % len(product_ids))
        self.pool.get('magento_sync').export_from_cat(cr, uid, cs, product_ids)

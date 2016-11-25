from openerp import fields, models, _
import logging
from optparse import OptionParser
from openerp.osv import osv

class ebay_sale_order(models.Model):
	_inherit = "sale.order"

	ebay_id = fields.Char(string="Ebay ID")
	ebay_date = fields.Datetime(string="Create date on ebay")
	ebay_username = fields.Char(string="Ebay customer username")
	ebay_instance_id = fields.Integer(string="Ebay instance ID")
	ebay_date_paid = fields.Datetime(string="Ebay paid date")
	ebay_date_shipped = fields.Datetime(string="Ebay shipped date")
	tmp_combine = fields.Integer(string="temp_combine")

	def ebay_open_message_wizard(self, cr, uid, ids, context=None):

		return {
			'type': 'ir.actions.act_window',
			'res_model': 'ebay.order.message',
			'view_type': 'form',
			'view_mode': 'form',
			'target':'new'
	}
	def ebay_cancel_order(self, cr, uid, ids, context=None):
		#_logger = logging.getLogger(__name__)
		sf = self.browse(cr, uid, ids, context=None)
		r = self.pool.get('ebay').browse(cr, uid, sf.ebay_instance_id, context=context)
		cert = r.cert_id
		dev = r.dev_id
		app = r.app_id
		tok = r.token_id

		order_line_item_ids = [x.order_line_item_id for x in sf.order_line]
		#print order_line_item_ids


		if r._cancel_order(cert, dev, app, tok, order_line_item_ids):
			#_logger.info("********ORDERED CANCELED")
			sf.write({'state':'cancel', 'ebay_id': False})
		else:
			raise osv.except_osv(_('Error canceling order'), _('This order cannot be canceled at a moment'))
		return True

	def ebay_is_canceled_order(self, cr, uid, ids, context=None):
		return self.write(cr, uid, ids, {'state': 'cancel'}, context=None)

	def _prepare_order_line_procurement(self, cr, uid, order, line, group_id=False, context=None):
		vals = super(ebay_sale_order, self)._prepare_order_line_procurement(cr, uid, order, line, group_id=group_id, context=context)
		vals.update({
			'ebay_transaction_id': line.transaction_id,
			'ebay_order_id': order.ebay_id,
			'ebay_item_id': line.ebay_item_id
		})

		return vals


class ebay_sale_order_line(models.Model):
	_inherit = "sale.order.line"

	transaction_id = fields.Char(string="Ebay transaction id")
	order_line_item_id = fields.Char(sting="Ebay OLID")
	ebay_item_id = fields.Char(string="Ebay Item ID")
	tmp_combine = fields.Integer(string="Wizard id - tmp")

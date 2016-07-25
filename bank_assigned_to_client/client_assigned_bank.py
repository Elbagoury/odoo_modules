from openerp import models, fields, api, _
class ResCompany(models.Model):
	_inherit = "res.company"

	is_bank_default = fields.Boolean(string="Is bank default?")
class ResPartner(models.Model):
	_inherit = "res.partner"

	@api.model
	def _get_bank_partner(self):

		cr = self._cr
		uid = self._uid
		ids = self._ids
		db = cr.dbname

		c = self.pool.get('res.company').search(cr, uid, [('is_bank_default', '=', True)], context=None)
		#print c
		if not c:
			return 0
		com = self.pool.get('res.company').browse(cr, uid, c, context=None)[0]
		#print com
		banks = com.bank_ids
		if not banks:
			return 0
		bank = banks[0]

		return bank.partner_id.id


	bank_pid = fields.Integer(default=lambda self: self._get_bank_partner(), string="Bank partner id")
	our_bank = fields.Many2one('res.partner.bank', string="Bank assigned to client")


class AccountInvoice(models.Model):
	_inherit = "account.invoice"
	@api.model
	def _get_bank_partner(self):

		cr = self._cr
		uid = self._uid
		ids = self._ids
		db = cr.dbname

		c = self.pool.get('res.company').search(cr, uid, [('is_bank_default', '=', True)], context=None)

		if not c:
			return 0
		com = self.pool.get('res.company').browse(cr, uid, c, context=None)[0]

		banks = com.bank_ids
		if not banks:
			return 0
		bank = banks[0]

		return bank.partner_id.id



	bank_pid = fields.Integer(default=lambda self: self._get_bank_partner(), string="Bank partner id")
	our_bank = fields.Many2one('res.partner.bank', string="Bank assigned to client")


	@api.multi
	def onchange_partner_id(self, type, partner_id, date_invoice=False,
            payment_term=False, partner_bank_id=False, company_id=False):
		print partner_id, type

		result = super(AccountInvoice, self).onchange_partner_id(type, partner_id, date_invoice, payment_term, partner_bank_id, company_id)

		if partner_id:
			partner = self.pool.get('res.partner').browse(self._cr, self._uid, partner_id, context=None)
		else:
			return result
		result['value'].update({

				'our_bank': partner.our_bank.id if partner.our_bank else 0

			})

		return result

	def create(self, cr, uid, vals, context=None):
		if vals['partner_id']:

			partner = self.pool.get('res.partner').browse(cr, uid, vals['partner_id'], context=None)

			if partner:

				vals['our_bank'] = partner.our_bank.id if partner.our_bank else 0
		res = super(AccountInvoice, self).create(cr, uid, vals, context=None)
		return res

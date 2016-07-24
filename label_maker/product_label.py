from openerp import fields, models

class product(models.Model):
	_inherit = "product.product"

	template = fields.Many2one('ir.actions.report.xml', domain="[('report_name','ilike','label_maker.%')]")
	
	company_prefix = fields.Char()
	


	def print_label_pdf(self, cr, uid, ids, context=None):
		for record in self.browse(cr, uid, ids, context=context):
			current_record = record
		if current_record.template:
			sel_temp = current_record.template

		model = sel_temp.report_name
			
		if not sel_temp:
			return False
		
		sel_temp.report_type = 'qweb-pdf'

		return self.pool.get('report').get_action(cr, uid, ids, model, context=context)

	def print_label_html(self, cr, uid, ids, context=None):
		for record in self.browse(cr, uid, ids, context=context):
			current_record = record
		if current_record.template:
			sel_temp = current_record.template

		model = sel_temp.report_name
			
		if not sel_temp:
			return False
		
		
		sel_temp.report_type = 'qweb-html'

		return self.pool.get('report').get_action(cr, uid, ids, model, context=context)
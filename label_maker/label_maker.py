from openerp import fields, models, api, _

class label_maker(models.Model):
	_name = "label.maker"

	is_created = fields.Boolean()
	view_name = fields.Char()
	view_id = fields.Many2one('ir.ui.view')
	rep_id = fields.Many2one('ir.actions.report.xml')
	eid_id = fields.Many2one('ir.model.data')
	ab_id = fields.Many2one('ir.values')
	view_arch = fields.Html()
	view_header = fields.Text()
	view_footer = fields.Text(default='a')
	name = fields.Char()
	report_model_name = fields.Char()
	report_template_name = fields.Char()
	variations = fields.One2many('label.variant', 'label_id')
	rel_id = fields.Integer()
	field_ids = fields.Many2one('ir.model.fields', 'Fields', domain=[('model', '=', 'product.product'), ('ttype', 'not in', ['one2many', 'refenrence', 'function'])])
	field_type = fields.Char()
	tag = fields.Selection((('h1', '<h1>'), ('h2', '<h2>'), ('h3', '<h3>'), ('p', '<p>')))
	variation_name = fields.Char()
	test_pro = fields.Many2one('product.product',  string="Product for testing")


	def create(self, cr, uid, values, context=None):
		name = values.get('name')
		view_name = values.get('view_name')
		view_arch = values.get('view_arch')


		header = "<t t-name='" + "label_maker." + view_name + "'><t t-call='report.html_container'><t t-foreach='docs' t-as='o'><div class='page'>"
		arch = view_arch
		footer = "</div></t></t></t>"

		values['view_header'] = header
		values['view_footer'] = footer
		values['is_created'] = True
		vals = {
			'name': view_name,
			'type': 'qweb',
			'arch': header + arch + footer
		}

		view_id = self.pool.get('ir.ui.view').create(cr, uid, vals, context)
		if view_id:
			#print "NEW VIEW CREATED WITH ID:" + str(view_id)
			values['view_id'] = view_id
			eid_vals = {
				'module': 'label_maker',
				'name': view_name,
				'model': 'ir.ui.view',
				'res_id': view_id
			}

			eid_id = self.pool.get('ir.model.data').create(cr, uid, eid_vals, context)
			values['eid_id'] = eid_id
			rep_vals = {
				'name': name,
				'model': 'product.product',
				'report_type': 'qweb-html',
				'report_name': 'label_maker.' + view_name
			}

			rep_id = self.pool.get('ir.actions.report.xml').create(cr, uid, rep_vals, context)

			if rep_id:
				#print "NEW REPORT CREATED WITH ID:" + str(rep_id)
				values['rep_id'] = rep_id
				ab_vals = {
					'name': name,
					'model': 'product.product',
					'key2': 'client_print_multi',
					'value_unpickle': 'ir.actions.report.xml,' + str(rep_id)
				}

				ab_id = self.pool.get('ir.values').create(cr, uid, ab_vals, context)
				values['ab_id'] = ab_id

		label = super(label_maker, self).create(cr, uid, values, context=context)
		lbl = self.browse(cr, uid, label, context=None)
		#print "CREATING LABEL"

		if 'name' in vals:
			client_ids = self.pool.get('res.partner').search(cr, uid, [("personalize", "=", True)], context=None)
			if client_ids:
				clients = self.pool.get('res.partner').browse(cr, uid, client_ids, context=None)
				for client in clients:
					var_name = client.name
					name = lbl.name + " - " +  var_name
					view_name = lbl.view_name + "_" + var_name
					view_arch = lbl.view_arch

					vals = {
						'name': name,
						'view_name': view_name,
						'view_arch': view_arch,
						'label_id': lbl.id,
						'customer_id': client.id
					}
					#print var_name
					var_id = self.pool.get('label.variant').create(cr, uid, vals, context=None)
					#print "CREATED LABEL VARIANT WITH ID " + str(var_id)

		return label

	def write(self, cr, uid, ids, vals, context=None):
		record = self.pool.get('label.maker').browse(cr, uid, ids, context=context)[0]
		if record:
			view = record['view_id']
			rep = record['rep_id']
		else:
			return False

		try:
			if view:
				a = record['view_header'] + vals['view_arch'] + record['view_footer']
				view.write({'arch': a})
		except:
			print "no arch changes"

		try:
			if view:
				view.write({'name': vals['view_name']})
		except:
			print "no name changes"

		try:
			if rep:
				rep.write({'name': vals['name']})
		except:
			print "no name changes"


		return super(label_maker, self).write(cr, uid, ids, vals, context=context)

	def unlink(self, cr, uid, ids, context=None):
		#print "**************IN UNLINK*********************"
		record = self.pool.get('label.maker').browse(cr, uid, ids, context=context)[0]
		if record:

			if record['rep_id']:
				rep = record['rep_id']
				self.pool.get('ir.actions.report.xml').unlink(cr, uid, rep.id, context=context)
				#print "deleted rep"

			for v in record['variations']:
				v.unlink()



		return super(label_maker, self).unlink(cr, uid, ids, context=context)



	def add_field(self, cr, uid, ids, context=None):
		if not ids:
			return True
		record = self.pool.get('label.maker').browse(cr, uid,ids, context=context)[0]
		#print "FIELD ID"
		#print record.field_ids.id
		field = self.pool.get('ir.model.fields').browse(cr, uid, record.field_ids.id, context=context)[0]

		field_name = field.name
		field_type = field.ttype
		#print field_name
		#print field_type
		if field_type in ['char', 'text', 'integer', 'float']:
			if record.tag:
				if record.tag == 'h1':
					name = "<h1 t-esc=\"o." + field_name + "\"></h1>"
				elif record.tag == 'h2':
					name = "<h2 t-esc=\"o." + field_name + "\"></h2>"
				elif record.tag == 'h3':
					name = "<h3 t-esc=\"o." + field_name + "\"></h3>"
				elif record.tag == 'p':
					name = "<p t-esc=\"o." + field_name + "\"></p>"
		elif field_type == 'binary':
			name = "<img t-if='o." + field_name + "' t-att-src=\"\'data:image/jpg;base64,%s\' % o." + field_name + "\"/>"
		else:
			name = "<span t-field=\"o." + field_name + "\"></span>"

		if record.view_arch:
			record.view_arch += name
		else:
			record.view_arch = name


		return True

	def edit_label_html(self, cr, uid, ids, context=None):
		for record in self.browse(cr, uid, ids, context=context):
			current_record = record
		if current_record.rep_id and current_record.test_pro:
			rep = current_record.rep_id
			test_pro = current_record.test_pro
		else:
			return False


		model = rep.report_name

		if not model:
			return False


		rep.report_type = 'qweb-html'

		return test_pro.pool.get('report').get_action(cr, uid, test_pro.id, model, context=context)

class label_variant(models.Model):
	_name = "label.variant"

	is_created = fields.Boolean()
	view_name = fields.Char()
	view_id = fields.Many2one('ir.ui.view')
	rep_id = fields.Many2one('ir.actions.report.xml')
	eid_id = fields.Many2one('ir.model.data')
	ab_id = fields.Many2one('ir.values')
	view_arch = fields.Html()
	view_header = fields.Text()
	view_footer = fields.Text(default='a')
	name = fields.Char()
	report_model_name = fields.Char()
	report_template_name = fields.Char()
	label_id = fields.Integer()
	customer_id = fields.Integer()
	field_ids = fields.Many2one('ir.model.fields', 'Fields', domain=[('model', '=', 'product.product'), ('ttype', 'not in', ['one2many', 'reference', 'function'])])
	field_type = fields.Char()
	tag = fields.Selection((('h1', '<h1>'), ('h2', '<h2>'), ('h3', '<h3>'), ('p', '<p>')))
	variation_name = fields.Char()
	test_pro = fields.Many2one('product.product',  string="Product for testing")


	def create(self, cr, uid, values, context=None):
		name = values.get('name')
		view_name = values.get('view_name')
		view_arch = values.get('view_arch')


		header = "<t t-name='" + "label_maker." + view_name + "'><t t-call='report.html_container'><t t-foreach='docs' t-as='o'><div class='page'>"
		arch = view_arch
		footer = "</div></t></t></t>"

		values['view_header'] = header
		values['view_footer'] = footer
		values['is_created'] = True
		vals = {
			'name': view_name,
			'type': 'qweb',
			'arch': header + arch + footer
		}

		view_id = self.pool.get('ir.ui.view').create(cr, uid, vals, context)
		if view_id:
			#print "NEW VIEW CREATED WITH ID:" + str(view_id)
			values['view_id'] = view_id
			eid_vals = {
				'module': 'label_maker',
				'name': view_name,
				'model': 'ir.ui.view',
				'res_id': view_id
			}

			eid_id = self.pool.get('ir.model.data').create(cr, uid, eid_vals, context)
			values['eid_id'] = eid_id
			rep_vals = {
				'name': name,
				'model': 'product.product',
				'report_type': 'qweb-html',
				'report_name': 'label_maker.' + view_name
			}

			rep_id = self.pool.get('ir.actions.report.xml').create(cr, uid, rep_vals, context)

			if rep_id:
				#print "NEW REPORT CREATED WITH ID:" + str(rep_id)
				values['rep_id'] = rep_id
				ab_vals = {
					'name': name,
					'model': 'product.product',
					'key2': 'client_print_multi',
					'value_unpickle': 'ir.actions.report.xml,' + str(rep_id)
				}

				ab_id = self.pool.get('ir.values').create(cr, uid, ab_vals, context)
				values['ab_id'] = ab_id

		return super(label_variant, self).create(cr, uid, values, context=context)

	def write(self, cr, uid, ids, vals, context=None):
		record = self.pool.get('label.maker').browse(cr, uid, ids, context=context)[0]
		if record:
			view = record['view_id']
			rep = record['rep_id']
		else:
			return False

		try:
			if view:
				a = record['view_header'] + vals['view_arch'] + record['view_footer']
				view.write({'arch': a})
		except:
			print "no arch changes"

		try:
			if view:
				view.write({'name': vals['view_name']})
		except:
			print "no name changes"

		try:
			if rep:
				rep.write({'name': vals['name']})
		except:
			print "no name changes"


		return super(label_variant, self).write(cr, uid, ids, vals, context=context)

	def unlink(self, cr, uid, ids, context=None):
		#print "**************IN UNLINK*********************"
		record = self.pool.get('label.variant').browse(cr, uid, ids, context=context)[0]
		if record:

			if record['rep_id']:
				rep = record['rep_id']
				self.pool.get('ir.actions.report.xml').unlink(cr, uid, rep.id, context=context)
				#print "deleted rep"
			if record['view_id']:
				record.view_id.unlink()
				#print "deleted view"

		return super(label_variant, self).unlink(cr, uid, ids, context=context)


	def add_field(self, cr, uid, ids, context=None):
		if not ids:
			return True
		record = self.pool.get('label.variant').browse(cr, uid,ids, context=context)[0]
		#print "FIELD ID"
		#print record.field_ids.id
		field = self.pool.get('ir.model.fields').browse(cr, uid, record.field_ids.id, context=context)[0]

		field_name = field.name
		field_type = field.ttype
		#print field_name
		#print field_type
		if field_type in ['char', 'text', 'integer', 'float']:
			if record.tag:
				if record.tag == 'h1':
					name = "<h1 t-esc=\"o." + field_name + "\"></h1>"
				elif record.tag == 'h2':
					name = "<h2 t-esc=\"o." + field_name + "\"></h2>"
				elif record.tag == 'h3':
					name = "<h3 t-esc=\"o." + field_name + "\"></h3>"
				elif record.tag == 'p':
					name = "<p t-esc=\"o." + field_name + "\"></p>"
		elif field_type == 'binary':
			name = "<img t-if='o." + field_name + "' t-att-src=\"\'data:image/jpg;base64,%s\' % o." + field_name + "\"/>"
		else:
			name = "<span t-field=\"o." + field_name + "\"></span>"

		if record.view_arch:
			record.view_arch += name
		else:
			record.view_arch = name


		return True

	def edit_label_html(self, cr, uid, ids, context=None):
		for record in self.browse(cr, uid, ids, context=context):
			current_record = record
		if current_record.rep_id and current_record.test_pro:
			rep = current_record.rep_id
			test_pro = current_record.test_pro
		else:
			return False


		model = rep.report_name

		if not model:
			return False


		rep.report_type = 'qweb-html'

		return test_pro.pool.get('report').get_action(cr, uid, test_pro.id, model, context=context)

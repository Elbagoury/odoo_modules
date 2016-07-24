from openerp import fields, models, api

class Boxes(models.Model):
	_name = "box"

	name= fields.Char(string="Name")
	#box properties
	width = fields.Float(string="Width (cm)")
	height = fields.Float(string="Height (cm)")
	length = fields.Float(string="Length (cm)")
	volume = fields.Float(string="Volume (m3)")
	weight = fields.Float(string="Weight (kg)")

	variants = fields.One2many('box.variant', 'box_id')

	def getVolumeAndWeight(self, cr, uid, ids, context=None):

		return True

def _create_labels(self, name, cid):

	cr = self._cr
	uid = self._uid
	label_ids = self.pool.get('label.maker').search(cr, uid, [('is_created', '!=', False)], context=None)
	if label_ids:
		labels = self.pool.get('label.maker').browse(cr, uid, label_ids, context=None)

		for label in labels:
			print label.view_name

			var_name = name
			name = label.name + " - " +  var_name
			view_name = label.view_name + "_" + var_name
			view_arch = label.view_arch

			vals = {
				'name': name,
				'view_name': view_name,
				'view_arch': view_arch,
				'label_id': label.id,
				'customer_id': cid
			}
			print var_name
			var_id = self.pool.get('label.variant').create(cr, uid, vals, context=None)
			print "CREATED LABEL VARIANT WITH ID " + str(var_id)
	return True

def _delete_labels(self):

	cr = self._cr
	uid = self._uid
	label_variant_ids = self.pool.get('label.variant').search(cr, uid, [('customer_id', '=', self.id)], context=None)
	return self.pool.get('label.variant').unlink(cr, uid, label_variant_ids, context=None)

def _create_boxes(self, name, cid):

			#validate it has name
			cr = self._cr
			uid = self._uid
			cust_name = name

			box_ids = self.pool.get('box').search(cr, uid, [("name", "!=", False)], context=None)
			if box_ids:
				boxes = self.pool.get('box').browse(cr, uid, box_ids, context=None)


				for box in boxes:

					vals = {
						'name': box.name + "_" + cust_name,
						'box_id': box.id,
						'customer_id': cid
					}
					self.pool.get('box.variant').create(cr, uid, vals, context=None)
					print vals

			return True


def _delete_boxes(self):

		cr = self._cr
		uid = self._uid
		box_variant_ids = self.pool.get('box.variant').search(cr, uid, [('customer_id', '=', self.id)], context=None)
		return self.pool.get('box.variant').unlink(cr, uid, box_variant_ids, context=None)


def _create_variants(self, name, cid):

		cr = self._cr
		uid = self._uid
		cust_name = name
		cat_ids = self.pool.get('product.category').search(cr, uid, [("not_customizable", "=", False)], context=None)
		pro_ids = self.pool.get('product.template').search(self._cr, self._uid, [("categ_id", "in", cat_ids)], context=None)

		products = self.pool.get('product.template').browse(self._cr, self._uid, pro_ids, context=None)

		for pro in products:

			pro_vals = {
				'default_code': pro.default_code + "_" + cust_name,
				'product_tmpl_id': pro.id,
				'customer_id': cid
			}

			new_pro_id = self.pool.get('product.product').create(self._cr, self._uid, pro_vals, context=None)


def _delete_variants(self):

		cr = self._cr
		uid = self._uid

		pro_variant_ids = self.pool.get('product.product').search(cr, uid, [("customer_id", '=', self.id)], context=None)
		return self.pool.get('product.product').unlink(cr, uid, pro_variant_ids, context=None)

def _create_variants_from_product(self, cr, uid, vals, context, pid):


		if 'categ_id' in vals:
			cat = self.pool.get('product.category').browse(cr, uid, vals['categ_id'], context=context)
			if cat.not_customizable == True:
				return True
			default_code = ''
			if 'default_code' in vals:
				default_code = vals['default_code']
			product_id = pid


			client_ids = self.pool.get('res.partner').search(cr, uid, [("personalize", "=", True)], context=context)
			clients = self.pool.get('res.partner').browse(cr, uid, client_ids, context=context)
			for client in clients:
				pro_vals = {
					'default_code': default_code + "_" + client.name,
					'product_tmpl_id': product_id,
					'customer_id': client.id
				}

				new_pro_id = self.pool.get('product.product').create(cr, uid, pro_vals, context=None)





class BoxVariant(models.Model):
	_name = "box.variant"

	name= fields.Char(string="Name")
	box_id = fields.Integer()
	#box properties
	width = fields.Float(string="Width (cm)")
	height = fields.Float(string="Height (cm)")
	length = fields.Float(string="Length (cm)")
	volume = fields.Float(string="Volume (m3)")
	weight = fields.Float(string="Weight (kg)")
	customer_id = fields.Integer()

class product_category(models.Model):
	_inherit = "product.category"

	not_customizable = fields.Boolean()

class product_product(models.Model):
	_inherit = "product.product"

	customer_id = fields.Integer()

class res_partner(models.Model):
	_inherit = "res.partner"

	personalize = fields.Boolean(string="Personalization")
	boxes = fields.One2many('box.variant', 'customer_id')
	labels = fields.One2many('label.variant', 'customer_id')

	@api.model
	def create(self, vals):

		partner = super(res_partner, self).create(vals)

		if 'customer' in vals and vals['customer'] == True and 'personalize' in vals and vals['personalize'] == True:
			_create_boxes(self, partner.name, partner.id)
			_create_variants(self, partner.name, partner.id)
			_create_labels(self, partner.name, partner.id)
		#except:
			#print "not personalize changes"

		return partner

	@api.multi
	def write(self, vals):

		result = super(res_partner, self).write(vals)

		if 'personalize' in vals:
			if vals['personalize']:
				_create_boxes(self, self.name, self.id)
				_create_variants(self, self.name, self.id)
				_create_labels(self, self.name, self.id)
			elif not vals['personalize']:
				_delete_boxes(self)
				_delete_variants(self)
				_delete_labels(self)
		
		return result

class product_template(models.Model):
	_inherit = "product.template"

	def create(self, cr, uid, vals, context=None):
			product_template_id = super(product_template, self).create(cr, uid, vals, context=context)
			if not context or "create_product_product" not in context:
				self.create_variant_ids(cr, uid, [product_template_id], context=context)

			related_vals = {}
			if vals.get('barcode'):
				related_vals['barcode'] = vals['barcode']
			if vals.get('default_code'):
				related_vals['default_code'] = vals['default_code']
			if vals.get('standard_price'):
				related_vals['standard_price'] = vals['standard_price']
			if vals.get('volume'):
				related_vals['volume'] = vals['volume']
			if vals.get('weight'):
				related_vals['weight'] = vals['weight']
			if related_vals:
				self.write(cr, uid, product_template_id, related_vals, context=context)

			_create_variants_from_product(self, cr, uid, vals, context, product_template_id)

			return product_template_id

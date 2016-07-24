from openerp import fields, models

class view(models.Model):
	_inherit="ir.ui.view"

	def write(self, cr, uid, ids, vals, context=None):
		if not isinstance(ids, (list, tuple)):
			ids = [ids]
		if context is None:
			context = {}

        # drop the corresponding view customizations (used for dashboards for example), otherwise
        # not all users would see the updated views
		custom_view_ids = self.pool.get('ir.ui.view.custom').search(cr, uid, [('ref_id', 'in', ids)])
		if custom_view_ids:
			self.pool.get('ir.ui.view.custom').unlink(cr, uid, custom_view_ids)

		self.clear_cache()

		try:
			arch = vals['arch']
		except:
			print "arch not changed"
		lab_ids = self.pool.get('label.maker').search(cr, uid, [('view_id', 'in', ids)], context=context)
		labels = self.pool.get('label.maker').browse(cr,uid, lab_ids, context=context)
		for label in labels:
			
			left = arch.rfind('<div class="page">')
			print left
			right = arch.find('</div>*\n</t>')
			print right
			
			length = len(arch)
			final = arch[left: length-right]
			print "final" + final
			#label.view_arch = final

		ret = super(view, self).write(
			cr, uid, ids,
			self._compute_defaults(cr, uid, vals, context=context),
			context)
		return ret
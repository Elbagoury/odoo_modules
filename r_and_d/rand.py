from openerp import fields, models


class ProductTemplate(models.Model):
	_inherit = "product.template"

	file_number = fields.Integer(string="Folder number")
	file_letter = fields.Char(string="File letter")
	cabinet_number = fields.Integer(string="Cabinet number")
	rd_files = fields.One2many('rand_files', 'product_id', string="R&D files")

	def insert_number(self,cr, uid, ids, context=None):
		pids = self.search(cr, uid, [('file_number', ">", 0)], context=None)
		new_cab_number = 1
		new_file_number = 1
		if pids:
			products = self.browse(cr, uid, pids, context=None)

			file_letter = [x.file_letter for x in products]
			latest_letter = max(file_letter or ["A"])

			cab_nos = [x.cabinet_number for x in products]
			latest_cab_no = max(cab_nos or [0])

			file_nos = [x.file_number for x in products if x.file_letter == latest_letter and x.cabinet_number == latest_cab_no]
			print file_nos
			latest_f_no = max(file_nos or [0])

			print latest_f_no, latest_letter, latest_cab_no
			new_cab_letter = latest_letter
			new_file_number += latest_f_no
			new_cab_number = latest_cab_no
			if new_file_number > 200:
				new_file_number = 1
				new_cab_number +=1
				if new_cab_number > 4:
					new_cab_number = 1
					if latest_letter == 'D':
						print "ERR"
						#raise

					new_cab_letter = 'B' if latest_letter == 'A' else 'C' if latest_letter == 'B' else 'D' if latest_letter == 'C' else 'X'
		else:
			new_cab_letter = "A"
			new_cab_number = 1
			new_file_number = 1


		rec = self.browse(cr, uid, ids, context=None)
		rec.file_letter = new_cab_letter
		rec.cabinet_number = new_cab_number
		rec.file_number = new_file_number


class rand_files(models.Model):
	_name = "rand_files"


	name = fields.Char(string="File name")
	file = fields.Binary(string="File")
	filename = fields.Char(string="Filename")
	product_id = fields.Integer(string="Product ID")

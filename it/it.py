from openerp import fields, models

class it_categories(models.Model):
	_name = "it.categories"

	name = fields.Char(string="Name")
	description = fields.Text(string="Description")
	nw_device = fields.Boolean(string="Is network device")

class it_brands(models.Model):
	_name = "it.brands"

	name = fields.Char(string="Name")

class it_components(models.Model):
	_name = "it.components"

	name = fields.Char(string="Name")
	description = fields.Char(string="Description")
	categ_id = fields.Many2one('it.categories', string="Category")
	brand = fields.Many2one('it.brands', string="Brand")
	serial_no = fields.Char(string="Serial_no")
	device_id = fields.Integer(string="Device ID")
	qty = fields.Float(string="Quantity")


class it_equipment(models.Model):
	_name = "it.equipment"

	name = fields.Char(string="Name")
	description = fields.Text(string="Description")
	categ_id = fields.Many2one('it.categories', string="Category")
	brand = fields.Many2one('it.brands', string="Brand")
	serial_no = fields.Char(string="Serial_no")
	components = fields.One2many('it.components', 'device_id', string="Components")
	
	ip_address = fields.Char(string="IP address")
	in_storage = fields.Boolean(string="In storage - obsolete")
	status = fields.Selection([('storage', "In storage"), ('in_use', "In use"), ('repair', 'Repair'), ('other', 'Other')], string="Status")
	assigned_to = fields.Many2one('hr.employee', string="Assigned to")
	active = fields.Boolean(string="Active", default=True)


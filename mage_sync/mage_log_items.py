from openerp import fields, models
import datetime

class Mage_log_items (models.Model):
  _name = "mage_log_item"

  sync_type = fields.Int()
  item_name = fields.Char()
  status = fields.Boolean()
  time = fields.Datetime()


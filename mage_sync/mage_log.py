from openerp import fields, models
import datetime

class Mage_logs_main(models.Model):
  _name = "mage_logs_main"


  name = fields.Char()
  sync_type = fields.Int()
  last_sync_begin = fields.Datetime()
  last_sync_end = fields.Datetime()
  status = fields.Boolean()
  status_desc = fields.Char(string='Last sync status')
  sync_counter = fields.Int()

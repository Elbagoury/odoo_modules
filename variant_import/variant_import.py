from openerp import fields, models, api, _
import logging
import csv
from datetime import datetime

class ImportVariants(models.TransientModel):
    _name = "import.variants"

    name = fields.Char(string="Name")
    delimiter = fields.Char(string="Delimiter")
    quote = fields.Char(string="Quotechar")
    sea_code_col = fields.Char(string="SEA code column index")
    client_code_col = fields.Char(srting="Client code column index")
    partner_id = fields.Many2one('res.partner', string="Client")

    attribute_id = fields.Many2one('product.attribute', string="Attribute ID")
    sea_value_id = fields.Many2one('product.attribute.value', string="SEA value")
    client_value_id = fields.Many2one('product.attribute.value', string="Client value")

    def import_file(self, cr, uid, ids, context=None):
        _logger = logging.getLogger(__name__)
        record = self.browse(cr,uid, ids, context=None)
        if not record:
            return True
        with open('home/gigra/variants.csv') as main:
                delim = record.delimiter.strip()
                quote = record.quote.strip()
                _logger.info("DELIM: %s, QUOTE: %s" % (delim, quote))
                rdr = csv.reader(main, delimiter=",", quotechar="\"")
                cnt = 0

                for r in rdr:
                    if not r[int(record.sea_code_col)]:
                        continue
                        cnt += 1

                    sea = r[int(record.sea_code_col)].strip()
                    client = r[int(record.client_code_col)].strip()
                    _logger.info("---Starting for %s - %s" % (client, sea))
                    variant_ids = self.pool.get('product.product').search(cr, uid, [('name', '=', sea), ('sale_ok', '=', True)])
                    variants = self.pool.get('product.product').browse(cr, uid, variant_ids, context=None)

                    if True:

                        for v in variants:
                            if v.attribute_value_ids:
                                continue
                            template = v.product_tmpl_id.id
                            attribute_line = self.pool.get('product.attribute.line').create(cr, uid,{'attribute_id':record.attribute_id.id, 'value_ids': [[6, False,[record.sea_value_id.id, record.client_value_id.id]]], 'product_tmpl_id':template}, context=None)

                            _logger.info("--_VA %s" % attribute_line)
                            v.default_code = sea
                            v.attribute_line_ids = [(6, False, [attribute_line])]
                            v.attribute_value_ids = [(6, False, [record.sea_value_id.id])]

                            new_var_id = self.pool.get('product.product').search(cr, uid, [('default_code', '=', sea), ('sale_ok','=', True,) ('attribute_line_ids', '=', attribute_line)], context=None)
                            _logger.info("--_NV %s" % new_var_id)
                            new_var = self.poll.get('product.product').browse(cr,uid, new_var_id, context=None)
                            new_var = new_var[0]
                            new_var.default_code = client

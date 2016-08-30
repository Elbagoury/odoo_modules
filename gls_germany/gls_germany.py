from openerp import fields, models, api, _

class gls_germany(models.Model):
    generate_file_for = fields.Boolean(string="Generate file for", help="Invoices with this courier selected will be included in GLS parcel file")

    def generate_file(self):
        cr = self._cr
        uid = self._uid
        inv_obj = self.pool.get('account.invoice')
        invoice_ids = inv_obj.search(cr, uid, [('gls_bot_passed', '=', False)], context=None)
        invoices = inv_obj.browse(cr, uid, invoice_ids, context=None)

        values = []
        for invoice in invoices:
            if invoice.generate_file_for:
                val = {
                    'type': 'B2B' if invoice.vat else 'NP',
                    'parcels': invoice.parcels,
                    'weight': invoice.weight,
                    'ref': invoice.number,
                    'company': invoice.shipping_partner_id.name if not invoice.shipping_partner_id.parent_id else invoice.shipping_partner_id.parent_id.name,
                    'name': invoice.shipping_partner_id.name if invoice.shipping_partner_id.parent_id else '',
                    'address': invoice.shipping_partner_id.street,
                    'coutry': invoice.shipping_partner_id.coutry_id.code,
                    'postcode': invoice.shipping_partner_id.zip,
                    'town': invoice.shipping_partner_id.city,
                    'telephone': invoice.shipping_partner_id.phone,
                    'msgtype1': 1,
                    'msglang1': 'DE'
                }
                values.append(val)
                invoice.gls_bot_passed = True
        with open('/opt/odoo/gigra_addons/gls_germany/file.csv', 'wb') as csvfile:
            writer = csv.writer(csvfile, delimiter=';',quotechar='\"', quoting=csv.QUOTE_MINIMAL)
            for val in values:
                writer.writerow([val['type']] + [val['parcels']]+ [val['weight']]+ [val['ref']]+ [val['company']]+ [val['name']]+ [val['address']]+ [val['country']]+ [val['postcode']]+ [val['town']]+ [val['telephone']]+ [val['msgtype1']]+ [val['msglang1']])



class account_invoice(models.Model):
    gls_bot_passed = fields.Boolean(string="GLS bot passed")

from openerp import fields, models, api, _
import logging
import ftplib
import csv
from datetime import datetime

class delivery_grid(models.Model):
    _inherit = 'delivery.grid'
    generate_file_for = fields.Boolean(string="Generate file for", help="Invoices with this courier selected will be included in DPD parcel file")

class dpd_germany(models.Model):
    _name="dpd.germany"

    name = fields.Char(string="Instance name")
    host = fields.Char(string="Host")
    user = fields.Char(string="User")
    password = fields.Char(string="Password")
    port = fields.Char(string="Port")
    path = fields.Char(string="Path")
    local_file_path = fields.Char(string="Local filepath")
    last_gen = fields.Datetime(string="Last file generation")

    def generate_file(self, cr, uid, ids, context):
        _logger = logging.getLogger(__name__)
        message = ''
        inv_obj = self.pool.get('account.invoice')
        invoice_ids = inv_obj.search(cr, uid, [('dpd_bot_passed', '=', False)], context=None)
        invoices = inv_obj.browse(cr, uid, invoice_ids, context=None)
        if not invoices:
            return
        record = self.browse(cr, uid, ids, context=None)[0]
        values = []
        for invoice in invoices:
            if not invoice.carrier_id:
                continue
            if invoice.carrier_id.generate_file_for:
                valx = {
                    'type': "NP,PAN,B2B" if invoice.partner_id.vat else 'NP,PAN,B2C',
                    'parcels': invoice.parcels,
                    'weight': invoice.total_weight,
                    'ref': invoice.number or 'N/A',
                    'company': invoice.address_shipping_id.name if not invoice.address_shipping_id.parent_id else invoice.address_shipping_id.parent_id.name,
                    'name': invoice.address_shipping_id.name,
                    'address': invoice.address_shipping_id.street,
                    'country': invoice.address_shipping_id.country_id.code,
                    'postcode': invoice.address_shipping_id.zip,
                    'town': invoice.address_shipping_id.city,
                    'telephone': invoice.address_shipping_id.phone,
                    'msgtype1': 1,
                    'msglang1': 'DE',
                    'email': invoice.partner_id.email or '',
                }
                res = self.pool.get('dpd.parcel').create(cr, uid, valx, context=None)
                _logger.info("_____res %s" % res)
                if res:
                    values.append(valx)
                    invoice.dpd_bot_passed = True
                    message += 'Creating parcel: Success '
        _logger.info(values)
        try:

            #CREATE FILE
            with open(record.local_file_path, 'wb') as csvfile:
                writer = csv.writer(csvfile, delimiter=';',quotechar='\"', quoting=csv.QUOTE_MINIMAL)
                _logger.info("2: %s" % values)
                writer.writerow(['Versandart'] + ['Anzahl Pakete']+ ['Gewicht (kg)']+ ['Referenznr. 1:'] + ['Referenznr. 2:'] + ['Sendungs ID'] +['Firma'] + ['Name']+['Zu Haenden']+ ['Adresse 1']+['Adresse 2']+ ['Land']+['Region']+ ['PLZ']+['MSGVALUE']+ ['Stadt']+ ['Tel.']+['Ref. (Adresse)']+['NN-Betrag']+['Waehrung']+['Verwendungszweck']+['Benachrichtigungstyp 1']+ ['Kontaktdaten 1 ']+['Benachrichtigungsereignis 1']+ ['Proaktive Benachr. Sprache 1 ']+['ID Check'] + ['ABT Gebaeude'] + ['ABT Stockwerk']+['ABT Abteilung']+['Hoeherversicherung Betrag']+['Hoeherversicherung Waehrung'] + ['Hoeherversicherung Wareninhalt'] + ['Export: Inhalt']+['Enthaelt Begleitpapiere']+['Export: Laenge']+['Export: Breite']+['Export: Hoehe']+['Export: Inhaltsbeschreibung 1']+['Export: Rechnungsempfaenger']+['Export: Rechnungsadresse 1']+['Export: Rechnungsland']+['Export: Region']+['Export: Rechnung PLZ']+['Export: Stadt']+['Export: Warenwert']+['Export: Waehrung'])

                for val in values:
                    _logger.info(val)
                    writer.writerow([val['type']] + [val['parcels']]+ [val['weight']]+ [val['ref']] + [''] + [''] +[val['company']] + [val['name']]+['']+ [val['address']]+['']+ [val['country']]+['']+ [val['postcode']]+[val['email']]+ [val['town']]+ [val['telephone']]+['']+['']+['']+['']+['']+ [val['msgtype1']]+['']+ [val['msglang1']])

            message += "Writing to file: Success "
        except:
            _logger.info("FAILED WRITING TO FILE")
            message += "Writing to file: FAILED "
        try:

            #Transfer the file
            host = record.host
            user = record.user
            password = record.password
            port = record.port or 21
            path = record.path

            ftp = ftplib.FTP(host)
            ftp.set_pasv(False)
            ftp.login(user=user, passwd=password)

            filename = record.local_file_path
            fn = 'file.csv'
            if path:
                ftp.cwd(path)
            response = ftp.storbinary('STOR ' + fn, open(filename, 'rb'))

            _logger.info(response)
            message += "Tranfer to ftp: %s" % response
            ftp.quit()
        except:
            message += "Transfering: FAILED"

        record.last_gen = datetime.now()
        log_vals = {
            'name': "Adding parcels",
            'message': message,
            'datetime': datetime.now(),
            'instance_id': record.id
        }
        self.pool.get('dpd.log').create(cr, uid, log_vals, context=None)

class dpd_parcel(models.Model):
    _name = "dpd.parcel"

    type = fields.Char(string="Type")
    parcels = fields.Integer(string="Parcels")
    weight = fields.Float(string="Weight")
    ref = fields.Char(string="Reference")
    company = fields.Char(string="Company")
    name = fields.Char(string="Name")
    address=fields.Char(string="Address")
    country = fields.Char(string="Country")
    postcode = fields.Char(string="Postcode")
    town = fields.Char(string="Town")
    telephone = fields.Char(string="Telephone")
    msgtype1 = fields.Integer(string="Message type")
    msglang1 = fields.Char(string="Message lang")
    invoice_id = fields.Integer(stirng="Invoice ID")
    email = fields.Char(string="Email")

class dpd_log(models.Model):
    _name = "dpd.log"

    datetime = fields.Datetime(sting="Date")
    name = fields.Char(string="Operation")
    message = fields.Char(string="Message")
    instance_id = fields.Many2one('dpd.germany', string="Instance", readonly="True")

class account_invoice(models.Model):
    _inherit = "account.invoice"

    dpd_bot_passed = fields.Boolean(string="DPD bot passed")

class stock_picking_package_preparation(models.Model):
    _inherit = 'stock.picking.package.preparation'

    net_weight = fields.Float(string="Net weight")

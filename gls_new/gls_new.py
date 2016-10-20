from openerp import fields, models, api, _
import logging
import ftplib
import csv
from datetime import datetime
from openerp.osv import osv

class delivery_grid(models.Model):
    _inherit = 'delivery.grid'
    generate_gls_file_for = fields.Boolean(string="Generate GLS file for", help="Invoices with this courier selected will be included in GLS parcel file")

class gls_service(models.Model):
    _name="gls"

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
        invoice_ids = inv_obj.search(cr, uid, [('gls_bot_passed', '=', False), ('carrier_id', '!=', False), ('carrier_id.generate_gls_file_for', '=', True)], context=None)
        _logger.info("----TOTAL NUMBER OF GLS INVOICES: %s" % len(invoice_ids))
        invoices = inv_obj.browse(cr, uid, invoice_ids, context=None)
        if not invoices:
            return

        ddt_obj = self.pool.get('stock.picking.package.preparation')
        ddt_ids = ddt_obj.search(cr, uid, [('gls_bot_passed', '=', False), ('carrier_id', '!=', False), ('carrier_id.generate_gls_file_for', '=', True)], context=None)
        _logger.info("----TOTAL NUMBER OF GLS DDTS: %s" % len(ddt_ids))
        ddts = ddt_obj.browse(cr, uid, ddt_ids, context=None)

        record = self.browse(cr, uid, ids, context=None)[0]
        values = []
        cnt = 0
        for invoice in invoices:
            #BREAKER ONLY DEBUG
            if cnt> 10:
                continue
            cnt += 1
            if not invoice.total_weight:
                raise osv.except_orm("GLS Labeling", "You must specify total weight")
            if not invoice.carriage_condition_id:
                raise osv.except_orm("GLS Labeling", "You must specify carriage condition (Franco/Contrassegno)")
            pts = ''

            if invoice.carriage_condition_id.name == "PORTO FRANCO":
                tipo_porto = "F"
            elif invoice.carriage_condition_id.name == "PORTO ASSEGNATO":
                tipo_porto = "A"

            else:
                tipo_porto = "F"
            shipping_partner = invoice.address_shipping_id

            vname = shipping_partner.parent_id.name if shipping_partner.parent_id else shipping_partner.name

            vstreet = shipping_partner.street

            vloc = shipping_partner.city
            importo_contrassegno = invoice.amount_total
            importo_contrassegno = str(importo_contrassegno)
            importo_contrassegno = importo_contrassegno.replace('.', ',')
            vweight = invoice.total_weight
            vweight = str(vweight)
            vweight = vweight.replace('.', ',')

            vnote = invoice.transportation_note or ''

            valx = {
                    'ragionesociale': vname,
                    'indirizzo': vstreet,
                    'localita': vloc,
                    'zipcode': invoice.address_shipping_id.zip,
                    'provincia': invoice.address_shipping_id.state_id.code or '',
                    'colli': invoice.parcels or 1,
                    'peso_reale': vweight,
                    'importo_contrassegno': importo_contrassegno,
                    'tipo_porto': tipo_porto,
                    'tipo_collo': '',#tipo_collo,
                    'document_name': invoice.number,
                    'cellulare': invoice.address_shipping_id.mobile,
                    'email': shipping_partner.email,
                    'note': vnote,
                    'invoice_id': invoice.id
            }
            res = self.pool.get('gls.new.parcel').create(cr, uid, valx, context=None)
            _logger.info("_____res %s" % res)
            if res:
                values.append(valx)
                invoice.gls_bot_passed = True
                message += 'Creating parcel for %s: Success ' % valx[document_name]
        cnt = 0
        for ddt in ddts:
            #BREAKER ONLY DEBUG
            if cnt> 10:
                continue
            cnt += 1
            if not ddt.total_weight:
                raise osv.except_orm("GLS Labeling", "You must specify total weight")
            if not ddt.carriage_condition_id:
                raise osv.except_orm("GLS Labeling", "You must specify carriage condition (Franco/Contrassegno)")
            pts = ''

            if ddt.carriage_condition_id.name == "PORTO FRANCO":
                tipo_porto = "F"
            elif ddt.carriage_condition_id.name == "PORTO ASSEGNATO":
                tipo_porto = "A"

            else:
                tipo_porto = "F"
            shipping_partner = ddt.partner_shipping_id

            vname = shipping_partner.parent_id.name if shipping_partner.parent_id else shipping_partner.name

            vstreet = shipping_partner.street

            vloc = shipping_partner.city
            importo_contrassegno = 0

            vweight = ddt.total_weight
            vweight = str(vweight)
            vweight = vweight.replace('.', ',')

            vnote = ddt.note or ''

            valx = {
                    'ragionesociale': vname,
                    'indirizzo': vstreet,
                    'localita': vloc,
                    'zipcode': ddt.partner_shipping_id.zip,
                    'provincia': ddt.partner_shipping_id.state_id.code or '',
                    'colli': ddt.parcels or 1,
                    'peso_reale': vweight,
                    'importo_contrassegno': importo_contrassegno,
                    'tipo_porto': tipo_porto,
                    'tipo_collo': '',#tipo_collo,
                    'document_name': ddt.name,
                    'cellulare': ddt.partner_shipping_id.mobile,
                    'email': shipping_partner.email,
                    'note': vnote,
                    'ddt_id': ddt.id
            }
            res = self.pool.get('gls.new.parcel').create(cr, uid, valx, context=None)
            _logger.info("_____res %s" % res)
            if res:
                values.append(valx)
                invoice.gls_bot_passed = True
                message += 'Creating parcel for %s: Success ' % valx[document_name]

        _logger.info(values)
        try:

            #CREATE FILE
            importo  = val['importo_contrassegno'] if val['tipo_porto'] == 'A' else ''


            text = ''
            for val in values:
                text += "%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;" % (val['ragionesociale'],val['indirizzo'],val['localita'],val['zipcode'],val['provincia'],val['document_name'],'',val['colli'],'',val['peso_reale'], importo,val['note'])

            with open(record.local_file_path, 'w') as file:
                file.write(text);

            message += "Writing to file: Success "
        except IOError:
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
        self.pool.get('gls.new.log').create(cr, uid, log_vals, context=None)

class gls_new_parcel(models.Model):
    _name = "gls.new.parcel"

    ragionesociale = fields.Char(required=True) #company name
    indirizzo = fields.Char(required=True) #address
    localita = fields.Char(required=True) #city
    zipcode = fields.Char(required=True)
    provincia = fields.Char(required=True) #province
    colli = fields.Integer(default=1)
    peso_reale = fields.Char(required=0) #real weight
    tipo_porto = fields.Char() #port type F-franco, A-attached
    tipo_collo = fields.Integer(default=0)
    cellulare = fields.Char()
    document_name = fields.Char(string="Document name")
    modalita_incasso = fields.Char()
    importo_contrassegno = fields.Char()
    note = fields.Text(string="Transportation note")
    status = fields.Char(string="Status")
    invoice_id = fields.Integer(string="Invoice ID")
    ddt_id = fields.Integer(string="DDT ID")
    date = fields.Char(string="Date")
    email = fields.Char(string="Email")

class gls_log(models.Model):
    _name = "gls.new.log"

    datetime = fields.Datetime(sting="Date")
    name = fields.Char(string="Operation")
    message = fields.Char(string="Message")
    instance_id = fields.Many2one('gls', string="Instance", readonly="True")

class account_invoice(models.Model):
    _inherit = "account.invoice"

    gls_bot_passed = fields.Boolean(string="GLS bot passed")

class stock_picking_package(models.Model):
    _inherit = "stock.picking.package.preparation"

    gls_bot_passed = fields.Boolean(string="GLS bot passed")

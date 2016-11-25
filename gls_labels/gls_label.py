import urllib2, urllib
import xml.etree.ElementTree as etree
import base64
from openerp import fields, models, _
import webbrowser
from openerp.osv import osv
import logging
import copy

class StockPickingPackagePreparation(models.Model):

	_inherit = 'stock.picking.package.preparation'

	total_weight = fields.Float(string="Weight")
	net_weight_gls = fields.Float(string="Net weight")
	gls_parcel = fields.One2many('gls.parcel', 'ddt_id', string="GLS parcel")
	label_binary = fields.Binary(string="GLS label binary")
	label_filename = fields.Char(string="GLS label")
	transportation_note = fields.Text(string="Transportation note")
	gls_config_id = fields.Many2one('gls.config', string="GLS contract")

	def gls_print(self, cr, uid, ids, context=None):
		#_logger = logging.getLogger(__name__)
		for invoice in self.browse(cr, uid, ids, context=context):
			curr_invoice = invoice
		config = curr_invoice.gls_config_id or self.pool.get('gls.config').browse(cr, uid,1, context=context)
		if config.sedeID is None:
			raise osv.except_orm("GLS Labeling", "COULD NOT GET CONFIG")

		colli = curr_invoice.parcels or 1
		progressive_counter = config.progressive_counter
		config.progressive_counter = progressive_counter

		if not curr_invoice.total_weight:
			raise osv.except_orm("GLS Labeling", "You must specify total weight")
		if not curr_invoice.carriage_condition_id:
			raise osv.except_orm("GLS Labeling", "You must specify carriage condition (Franco/Contrassegno)")
		pts = ''
		if curr_invoice.carriage_condition_id.name == "PORTO FRANCO":
			tipo_porto = "F"
		elif curr_invoice.carriage_condition_id.name == "PORTO ASSEGNATO":
			tipo_porto = "A"

		else:
			tipo_porto = "F"


		invoice_name = curr_invoice.ddt_number
		if not invoice_name:
			raise osv.except_orm("GLS Labeling", "This Ddt has no name!")
		invoice_name = invoice_name.replace("/", "-")
		client = curr_invoice.partner_id
		shipping_partner = curr_invoice.partner_shipping_id or client
		#_logger.info("PARTNER %s " % shipping_partner)
		if not shipping_partner.street or not shipping_partner.zip or not shipping_partner.city or not shipping_partner.state_id:
			raise osv.except_osv(_("GLS LABEL PRINT"), _("Missing information on client.  Client must have street, city, zip code and state (province). If invoice has shipping address defined, that is considered, if no, main invoice partner is considered "))

		vname = shipping_partner.name
		vname = vname.replace("&", "&amp;")
		vname = vname.replace("'", "&#39;")
		vname = vname.replace("\"", "&quot;")

		vstreet = shipping_partner.street
		vstreet = vstreet.replace("&", "&amp;")
		vstreet = vstreet.replace("'", "&#39;")
		vstreet = vstreet.replace("\"", "&quot;")

		vloc = shipping_partner.city
		vloc = vloc.replace("&", "&amp;")
		vloc = vloc.replace("'", "&#39;")
		vloc = vloc.replace("\"", "&quot;")
		vweight = curr_invoice.total_weight
		if colli > 1:
			vweight = vweight / colli
		vweight = str(vweight)
		vweight = vweight.replace('.', ',')



		vnote = curr_invoice.transportation_note or ''
		vnote = vnote.replace("&", "&amp;")
		vnote = vnote.replace("'", "&#39;")
		vnote = vnote.replace("\"", "&quot;")

		prcls = 0
		for i in range(0, colli):

			vals = {
				'ragionesociale': vname,
				'indirizzo': vstreet,
				'localita': vloc,
				'zipcode': shipping_partner.zip,
				'provincia': shipping_partner.state_id.code,
				'peso_reale': vweight,
				'tipo_porto': tipo_porto,
				'cellulare1': shipping_partner.mobile or '',
				'email': shipping_partner.email or '',
				'importo_contrassegno': '0',
				'modalita_incasso': '',
				'extra_filename': invoice_name,
				'contatore_progressivo': progressive_counter,
				'colli': 1,
				'note': vnote,
				'ddt_id': curr_invoice.id,
				'config_id': config.id
			}
			counter = self.pool.get('gls.parcel').create(cr, uid, vals, context=context)
			prcls +=1
			if not counter:
				raise osv.except_orm("GLS Labeling", "Fatal: Error creating parcel in local")


			#print "CREATED GLS PARCEL LOCAL WITH ID: " + str(counter)
			#print vals

			parcel = self.pool.get('gls.parcel').browse(cr, uid, counter, context=context)[0]
			if not parcel:
				#print "Parcel not retrieved"
				return False



			infostring = "<Info><SedeGls>" + config.sedeID+ "</SedeGls><CodiceClienteGls>"+config.glsUser+"</CodiceClienteGls><PasswordClienteGls>"+config.glsPass+"</PasswordClienteGls>"
			infostring += getInfoString(parcel, config.glsContract, ddt=True)
			infostring += "</Info>"
			if infostring is None:
				#print "No infostring"
				return False

			with open('/opt/odoo/gigra_addons/gls_labels/infostring.xml', 'w') as f:
					f.write(infostring)
			mydata=[('XMLInfoParcel',infostring)]
			mydata=urllib.urlencode(mydata)
			path='https://weblabeling.gls-italy.com/IlsWebService.asmx/AddParcel'
			req=urllib2.Request(path, mydata)
			req.add_header("Content-type", "application/x-www-form-urlencoded")

			page=urllib2.urlopen(req).read()
			if True:
				with open('/opt/odoo/gigra_addons/gls_labels/parcel.xml', 'w') as f:
					f.write(page)
				with open('/opt/odoo/gigra_addons/gls_labels/parcel.xml', 'r') as f:
					tree = etree.parse(f)
					root = tree.getroot()
					#print root.tag
					child = root[0]
					sped_num = child.find('NumeroSpedizione')
					if sped_num is None:
						#print "Sped num not retrieved"
						return False
					if sped_num.text == '999999999':
						mess = child.find('NoteSpedizione')
						self.pool.get('gls.parcel').unlink(cr, uid, counter, context=None)
						raise osv.except_osv(_("GLS LABEL PRINT"), _(mess.text))



					sigla = child.find('SiglaMittente')
					tot_colli = child.find('TotaleColli')
					t_collo = child.find('TipoCollo')
					dest = child.find('SiglaSedeDestino')
					date = child.find('DataSpedizione')
					comp_sped = "%s %s %s %s %s" % (sigla.text, sped_num.text, tot_colli.text, t_collo.text, dest.text)
					self.pool.get('gls.parcel').write(cr, uid, counter, {'date':date,'numero_spedizione': sped_num.text, 'name': comp_sped, 'status': 'Pending closure'}, context=context)
					#print "SPED NUMBER: " + sped_num.text

					#print child.tag
					label = child.find('PdfLabel')
					decoded = base64.b64decode(label.text)

					parcel.label_binary = label.text
					parcel.label_filename = "gls-%s.pdf" % invoice_name



class gls_invoice(models.Model):
	_inherit="account.invoice"

	total_weight = fields.Float(string="Total weight")
	net_weight = fields.Float(string="Net weight")

	parcels = fields.Integer(string="Parcels")
	gls_parcel = fields.One2many('gls.parcel', 'invoice_id', string="GLS parcel")
	label_binary = fields.Binary(string="GLS label binary")
	label_filename = fields.Char(string="GLS label")
	transportation_note = fields.Text(string="Transportation note")
	gls_config_id = fields.Many2one('gls.config', string="GLS contract")


	def gls_print(self, cr, uid, ids, context=None):
		#_logger = logging.getLogger(__name__)
		for invoice in self.pool.get('account.invoice').browse(cr, uid, ids, context=context):
			curr_invoice = invoice
		config = curr_invoice.gls_config_id or self.pool.get('gls.config').browse(cr, uid,1, context=context)
		if config.sedeID is None:
			raise except_orm("GLS Labeling", "COULD NOT GET CONFIG")
		payment_term = curr_invoice.payment_term.name if curr_invoice.payment_term else None
		contrassegno = 0
		if payment_term == 'CONT':
			contrassegno = 1
		colli = curr_invoice.parcels or 1
		progressive_counter = config.progressive_counter
		config.progressive_counter = progressive_counter

		if not curr_invoice.total_weight:
			raise except_orm("GLS Labeling", "You must specify total weight")
		if not curr_invoice.carriage_condition_id:
			raise except_orm("GLS Labeling", "You must specify carriage condition (Franco/Contrassegno)")
		pts = ''
		if curr_invoice.carriage_condition_id.name == "PORTO FRANCO":
			tipo_porto = "F"
		elif curr_invoice.carriage_condition_id.name == "PORTO ASSEGNATO":
			tipo_porto = "A"

		else:
			tipo_porto = "F"


		invoice_name = curr_invoice.number
		if not invoice_name:
			raise except_orm("GLS Labeling", "You can only ship validated invoices! Please validate\nFattura non ha alcun numero")
		invoice_name = invoice_name.replace("/", "-")
		client = curr_invoice.partner_id
		shipping_partner = curr_invoice.address_shipping_id or client
		#_logger.info("PARTNER %s " % shipping_partner)
		if not shipping_partner.street or not shipping_partner.zip or not shipping_partner.city or not shipping_partner.state_id:
			raise osv.except_osv(_("GLS LABEL PRINT"), _("Missing information on client.  Client must have street, city, zip code and state (province). If invoice has shipping address defined, that is considered, if no, main invoice partner is considered "))

		vname = shipping_partner.name
		vname = vname.replace("&", "&amp;")
		vname = vname.replace("'", "&#39;")
		vname = vname.replace("\"", "&quot;")

		vstreet = shipping_partner.street
		vstreet = vstreet.replace("&", "&amp;")
		vstreet = vstreet.replace("'", "&#39;")
		vstreet = vstreet.replace("\"", "&quot;")

		vloc = shipping_partner.city
		vloc = vloc.replace("&", "&amp;")
		vloc = vloc.replace("'", "&#39;")
		vloc = vloc.replace("\"", "&quot;")
		vweight = curr_invoice.total_weight
		if colli > 1:
			vweight = vweight / colli
		vweight = str(vweight)
		vweight = vweight.replace('.', ',')

		vtotal = curr_invoice.amount_total if contrassegno == 1 else 0
		vtotal = str(vtotal)
		vtotal = vtotal.replace('.', ',')

		vnote = curr_invoice.transportation_note or ''
		vnote = vnote.replace("&", "&amp;")
		vnote = vnote.replace("'", "&#39;")
		vnote = vnote.replace("\"", "&quot;")

		prcls = 0
		for i in range(0, colli):
			vals = {
				'ragionesociale': vname,
				'indirizzo': vstreet,
				'localita': vloc,
				'zipcode': shipping_partner.zip,
				'provincia': shipping_partner.state_id.code, #TODO: add field province to partner
				'peso_reale': vweight,
				'tipo_porto': tipo_porto,
				'cellulare1': shipping_partner.mobile or '',
				'email': shipping_partner.email or '',
				'importo_contrassegno': vtotal,
				'modalita_incasso': "ARM" if contrassegno == 1 else '',
				'extra_filename': invoice_name,
				'contatore_progressivo': progressive_counter,
				'colli': 1,
				'note': vnote,

				'config_id': config.id
			}
			counter = self.pool.get('gls.parcel').create(cr, uid, vals, context=context)
			prcls +=1
			if not counter:
				raise except_orm("GLS Labeling", "Fatal: Error creating parcel in local")


			#print "CREATED GLS PARCEL LOCAL WITH ID: " + str(counter)
			#print vals

			parcel = self.pool.get('gls.parcel').browse(cr, uid, counter, context=context)[0]
			if not parcel:
				#print "Parcel not retrieved"
				return False




			infostring = "<Info><SedeGls>" + config.sedeID+ "</SedeGls><CodiceClienteGls>"+config.glsUser+"</CodiceClienteGls><PasswordClienteGls>"+config.glsPass+"</PasswordClienteGls>"
			infostring += getInfoString(parcel, config.glsContract)
			infostring += "</Info>"
			if infostring is None:
				#print "No infostring"
				return False

			with open('/opt/odoo/gigra_addons/gls_labels/infostring.xml', 'w') as f:
					f.write(infostring)
			mydata=[('XMLInfoParcel',infostring)]
			mydata=urllib.urlencode(mydata)
			path='https://weblabeling.gls-italy.com/IlsWebService.asmx/AddParcel'
			req=urllib2.Request(path, mydata)
			req.add_header("Content-type", "application/x-www-form-urlencoded")

			page=urllib2.urlopen(req).read()
			if True:
				with open('/opt/odoo/gigra_addons/gls_labels/parcel.xml', 'w') as f:
					f.write(page)
				with open('/opt/odoo/gigra_addons/gls_labels/parcel.xml', 'r') as f:
					tree = etree.parse(f)
					root = tree.getroot()
					#print root.tag
					child = root[0]
					sped_num = child.find('NumeroSpedizione')
					if sped_num is None:
						#print "Sped num not retrieved"
						return False
					if sped_num.text == '999999999':
						mess = child.find('NoteSpedizione')
						self.pool.get('gls.parcel').unlink(cr, uid, counter, context=None)
						raise osv.except_osv(_("GLS LABEL PRINT"), _(mess.text))


				#MAGENTO SHIPMENT
					magento_id = curr_invoice.magento_id
					mage_shipp_id = None
					if magento_id:

						#_logger.warning("*****THIS ORDER IS IMPORTED FROM MAGENTO, INITIATING SHIPPING EXPORT PROCEDURE - %s ******" % magento_id)
						#print "*****THIS ORDER IS IMPORTED FROM MAGENTO, INITIATING SHIPPING EXPORT PROCEDURE - %s ******" % magento_id
						inv_obj = curr_invoice
						items = []
						for item in inv_obj.source.order_line:

								#print "******"
								#print i.magento_id
								#_logger.warning("**** %s" % i.magento_id)
								items.append({"order_item_id":item.magento_id, "qty": item.product_uom_qty})

						if items:
								for record in self.pool.get('magento_sync').browse(cr, uid, 1, context=context):
									r = record

								cs = {
									'location': r.mage_location,
									'port': r.mage_port,
									'user': r.mage_user,
									'pwd': r.mage_pwd
								}
								mage_shipp_id = self.pool.get('magento_sync').export_shipment(magento_id, items, sped_num.text, cs)
								if not mage_shipp_id:
									#print "MAGENTO SHIPP ERROR"
									#raise except_orm("MAGENTO CONNECTOR", "SHIPPMENT CANNOT BE EXPORTED TO MAGENTO STORE")
				#END MAGENTO SHIPPMENT
					sigla = child.find('SiglaMittente')
					tot_colli = child.find('TotaleColli')
					t_collo = child.find('TipoCollo')
					dest = child.find('SiglaSedeDestino')
					date = child.find('DataSpedizione')
					comp_sped = "%s %s %s %s %s" % (sigla.text, sped_num.text, tot_colli.text, t_collo.text, dest.text)
					parcel.date = date
					parcel.numero_spedizione = sped_num.text
					parcel.name = comp_sped
					parcel.status = 'Pending closure'
					parcel.magento_id = mage_shipp_id or 0
					#self.pool.get('gls.parcel').write(cr, uid, counter, {'date':date,'numero_spedizione': sped_num.text, 'name': comp_sped, 'status': 'Pending closure', 'magento_id': mage_shipp_id or 0}, context=context)
					#print "SPED NUMBER: " + sped_num.text

					#print child.tag
					label = child.find('PdfLabel')
					decoded = base64.b64decode(label.text)

					parcel.label_binary = label.text
					parcel.label_filename = "gls-%s.pdf" % invoice_name
					curr_invoice.gls_parcel = [[4,parcel.id]]
					#print "OK"
		if not curr_invoice.sent:
			self.pool.get('email.template').send_mail(cr, uid, 12, curr_invoice.id)
			curr_invoice.sent = True
		#except:
		#	print "Fatal: Error writing xml/pdf file to disk!"
		#	return False


		return True

def getInfoString(parcel, contract, total=False, ddt=False):
	#_logger = logging.getLogger(__name__)
	#_logger.info("CONTRACT: %s, PROPS:%s " % (contract, [parcel.ragionesociale, parcel.indirizzo, parcel.modalita_incasso, parcel.importo_contrassegno]))
	if total:
		w = parcel.peso_reale.replace(',', '.')
		w = float(w)
		return "<Parcel><CodiceContrattoGls>"+contract+"</CodiceContrattoGls><RagioneSociale>" + parcel.ragionesociale + "</RagioneSociale><Indirizzo>" + parcel.indirizzo +"</Indirizzo><Localita>"+parcel.localita+"</Localita><Zipcode>"+parcel.zipcode+"</Zipcode><Provincia>"+parcel.provincia+"</Provincia><Colli>"+str(parcel.colli)+"</Colli><PesoReale>"+str(w * float(parcel.colli)).replace('.', ',')+"</PesoReale><NoteSpedizione>"+parcel.note+"</NoteSpedizione><ModalitaIncasso>"+parcel.modalita_incasso+"</ModalitaIncasso><TipoPorto>"+str(parcel.tipo_porto)+"</TipoPorto><ImportoContrassegno>"+parcel.importo_contrassegno+"</ImportoContrassegno><Cellulare1>"+parcel.cellulare1+"</Cellulare1><Email>"+parcel.email+"</Email><TipoCollo>"+str(parcel.tipo_collo)+"</TipoCollo><GeneraPdf>2</GeneraPdf><Bda>"+parcel.extra_filename+"</Bda></Parcel>"
	if ddt:
		return "<Parcel><CodiceContrattoGls>"+contract+"</CodiceContrattoGls><RagioneSociale>" + parcel.ragionesociale + "</RagioneSociale><Indirizzo>" + parcel.indirizzo +"</Indirizzo><Localita>"+parcel.localita+"</Localita><Zipcode>"+parcel.zipcode+"</Zipcode><Provincia>"+parcel.provincia+"</Provincia><Colli>"+str(parcel.colli)+"</Colli><PesoReale>"+str(parcel.peso_reale)+"</PesoReale><NoteSpedizione>"+parcel.note+"</NoteSpedizione><ModalitaIncasso>"+parcel.modalita_incasso+"</ModalitaIncasso><TipoPorto>"+str(parcel.tipo_porto)+"</TipoPorto><ImportoContrassegno>0</ImportoContrassegno><Cellulare1>"+parcel.cellulare1+"</Cellulare1><Email>"+parcel.email+"</Email><TipoCollo>"+str(parcel.tipo_collo)+"</TipoCollo><GeneraPdf>2</GeneraPdf><Bda>"+parcel.extra_filename+"</Bda><ContatoreProgressivo>"+str(parcel.contatore_progressivo)+"</ContatoreProgressivo></Parcel>"
	return "<Parcel><CodiceContrattoGls>"+contract+"</CodiceContrattoGls><RagioneSociale>" + parcel.ragionesociale + "</RagioneSociale><Indirizzo>" + parcel.indirizzo +"</Indirizzo><Localita>"+parcel.localita+"</Localita><Zipcode>"+parcel.zipcode+"</Zipcode><Provincia>"+parcel.provincia+"</Provincia><Colli>"+str(parcel.colli)+"</Colli><PesoReale>"+str(parcel.peso_reale)+"</PesoReale><NoteSpedizione>"+parcel.note+"</NoteSpedizione><ModalitaIncasso>"+parcel.modalita_incasso+"</ModalitaIncasso><TipoPorto>"+str(parcel.tipo_porto)+"</TipoPorto><ImportoContrassegno>"+parcel.importo_contrassegno+"</ImportoContrassegno><Cellulare1>"+parcel.cellulare1+"</Cellulare1><Email>"+parcel.email+"</Email><TipoCollo>"+str(parcel.tipo_collo)+"</TipoCollo><GeneraPdf>2</GeneraPdf><Bda>"+parcel.extra_filename+"</Bda><ContatoreProgressivo>"+str(parcel.contatore_progressivo)+"</ContatoreProgressivo></Parcel>"

class gls_parcel(models.Model):
	_name = "gls.parcel"

	name = fields.Char(string="Name")
	ragionesociale = fields.Char(required=True) #company name
	indirizzo = fields.Char(required=True) #address
	localita = fields.Char(required=True) #city
	zipcode = fields.Char(required=True)
	provincia = fields.Char(required=True) #province
	colli = fields.Integer(default=1)
	peso_reale = fields.Char(required=0) #real weight
	tipo_porto = fields.Char() #port type F-franco, A-attached
	tipo_collo = fields.Integer(default=0)
	email = fields.Char()
	cellulare1 = fields.Char()
	modalita_incasso = fields.Char()
	importo_contrassegno = fields.Char()
	genera_pdf = fields.Integer(default=2) #0-no and disable, 1-yes but do not return, 2-create and return
	contatore_progressivo = fields.Integer() #progressive counter
	extra_filename = fields.Char() #invoice name for naming pdf file created
	numero_spedizione = fields.Char() #sped number, added after label creation
	note = fields.Text(string="Transportation note")
	status = fields.Char(string="Status")
	invoice_id = fields.Integer(string="Invoice ID")
	ddt_id = fields.Integer(string="DDT ID")
	magento_id = fields.Integer(string="magento_id")
	label_binary = fields.Binary(string="GLS label binary")
	label_filename = fields.Char(string="GLS label")
	config_id = fields.Integer(string="Config ID")
	date = fields.Char(string="Date")
	#ddt_id = fields.Integer(string="Ddt_id")

	def unlink(self, cr, uid, ids, context=None):
		#_logger = logging.getLogger(__name__)
		#return super(gls_parcel, self).unlink(cr, uid, ids, context=context)
		#print "**************IN UNLINK*********************"
		config = self.pool.get('gls.config').browse(cr, uid, 1, context=context)
		if config.sedeID is None:
			#print "coundnt retrieve configurations"
			raise osv.except_osv(_("GLS PARCEL CANCELATION"), _("COULDNT RETRIEVE CONFIGURATION"))

		record = self.pool.get('gls.parcel').browse(cr, uid, ids, context=context)[0]
		if record.numero_spedizione:
			try:
				mydata=[('SedeGls',""+ config.sedeID+""), ('CodiceClienteGls', ""+config.glsUser+""), ('PasswordClienteGls', ""+config.glsPass+""), ('NumSpedizione', record.numero_spedizione)]
				mydata=urllib.urlencode(mydata)
				path='https://weblabeling.gls-italy.com/IlsWebService.asmx/DeleteSped'
				req=urllib2.Request(path, mydata)
				req.add_header("Content-type", "application/x-www-form-urlencoded")
				page=urllib2.urlopen(req).read()

				#print "DeletedSPEDITION(S)"

			except:
				#print "Failed to delete from webserver"
				raise osv.except_osv(_("GLS PARCEL CANCELATION"), _("FAILED TO CANCEL PARCEL %s" % record.numero_spedizione))


		return super(gls_parcel, self).unlink(cr, uid, ids, context=context)



class gls_cofig(models.Model):
	_name = "gls.config"
	_inherit = 'res.config.settings'

	def name_get(self, cr, uid, ids, context=None):
	    if context is None:
	        context = {}
	    if isinstance(ids, (int, long)):
	        ids = [ids]

	    res = []
	    for record in self.browse(cr, uid, ids, context=context):
	        name = record.name
	        res.append((record.id, name))

	    return res

	name = fields.Char(required=True)
	sedeID = fields.Char(required=True)
	glsUser = fields.Char(required=True)
	glsPass = fields.Char(required=True)
	glsContract = fields.Char(required=True)
	cron_id = fields.Many2one('ir.cron', domain="[('model', '=ilike', 'gls%')]")
	progressive_counter = fields.Integer(string="Progressive counter", default="1")
	confirmation_email_template = fields.Many2one('email.template', string="Tracking number email template")

	def create_cron(self, cr, uid, ids, context=None):
		cr_vals = {
			'active': True,
			'display_name': 'Gls Close Workday',
			'function': 'closeWorkDay',
			'interval_number': 1,
			'interval_type': 'days',
			'model': 'gls.config',
			'name': 'Gls Close Workday',
			'numbercall': -1,
			'priority': 1
		}
		cron = self.pool.get('ir.cron').create(cr, uid, cr_vals, context=context)
		self.write(cr, uid, ids, {'cron_id': cron}, context=context)
		return True

	def closeWorkDay(self, cr, uid, ids, context=None):
		#_logger = logging.getLogger(__name__)
		config = self.browse(cr, uid, ids, context=context)
		if not config:
			raise except_orm("GLS CWD", "COULD NOT GET CONFIG")

		config = config[0]
		parcel_ids = self.pool.get('gls.parcel').search(cr, uid, [('status', '=', 'Pending closure'), ('config_id', '=', config.id)], context=context)
		#print len(parcel_ids)

		records = self.pool.get('gls.parcel').browse(cr, uid, parcel_ids, context=context)
		#print "*******************************************************"
		if records is None:
			raise except_orm("GLS Labeling", "NO PARCELS TO CLOSE")

		#print records
		grouped = []
		used = []

		for record in records:
			if record.numero_spedizione in used:
				continue

			tmp = [y.numero_spedizione for y in records].count(record.numero_spedizione)

			tmp_parcel = record
			tmp_parcel.colli = tmp
			grouped.append(tmp_parcel)

			used.append(record.numero_spedizione)

		#_logger.info("------GROUPED PARCELS-------")
		#_logger.info(grouped, [z['colli'] for z in grouped])
#

#
		infostrings = ''
		for g in grouped:
			vname = g.name
			vname = vname.replace("&", "&amp;")
			vname = vname.replace("'", "&#39;")
			vname = vname.replace("\"", "&quot;")

			vind = g.indirizzo
			vind = vind.replace("&", "&amp;")
			vind = vind.replace("'", "&#39;")
			vind = vind.replace("\"", "&quot;")

			vcitta = g.localita
			vcitta = vcitta.replace("&", "&amp;")
			vcitta = vcitta.replace("'", "&#39;")
			vcitta = vcitta.replace("\"", "&quot;")




			infostrings += getInfoString(g, config.glsContract, total=True)



		infostring = "<Info><SedeGls>" + config.sedeID+ "</SedeGls><CodiceClienteGls>"+config.glsUser+"</CodiceClienteGls><PasswordClienteGls>"+config.glsPass+"</PasswordClienteGls>"
		infostring += infostrings
		infostring += "</Info>"

		#_logger.info("------FINAL-----")
		#_logger.info(infostring)
		with open('/opt/odoo/gigra_addons/gls_labels/cwd_is.xml', 'w') as f:
			f.write(infostring)

		mydata=[('XMLCloseInfoParcel',infostring)]
		mydata=urllib.urlencode(mydata)
		path='https://weblabeling.gls-italy.com/IlsWebService.asmx/CloseWorkDay'
		req=urllib2.Request(path, mydata)
		req.add_header("Content-type", "application/x-www-form-urlencoded")
		page=urllib2.urlopen(req).read()

		try:
			with open('/opt/odoo/gigra_addons/gls_labels/cwd.xml', 'w') as f:
				f.write(page)
			with open('/opt/odoo/gigra_addons/gls_labels/cwd.xml', 'r') as f:
				tree = etree.parse(f);
				root = tree.getroot()
				#print root.tag
				#print root.text
				#print "PROGRAM OK"

		except:
			#print "Fatal: Error writing xml/pdf file to disk!"
			return False

		mydata=[('SedeGls',""+ config.sedeID+""), ('CodiceClienteGls', ""+config.glsUser+""), ('PasswordClienteGls', ""+config.glsPass+"")]
		mydata=urllib.urlencode(mydata)
		path='https://weblabeling.gls-italy.com/IlsWebService.asmx/ListSped'
		req=urllib2.Request(path, mydata)
		req.add_header("Content-type", "application/x-www-form-urlencoded")
		page=urllib2.urlopen(req).read()

		try:
			with open('/opt/odoo/gigra_addons/gls_labels/cwd.xml', 'w') as f:
				f.write(page)
			with open('/opt/odoo/gigra_addons/gls_labels/cwd.xml', 'r') as f:
				tree = etree.parse(f);
				root = tree.getroot()
				children = []
				for r in root:
					children.append(r)
				for child in children:
					number = child.find('NumSpedizione').text
					status = child.find('StatoSpedizione').text
					#print number
					#print status
					if status == "CHIUSA.":
						child_id = self.pool.get('gls.parcel').search(cr, uid, [('numero_spedizione', '=', number)], context=context)

						self.pool.get('gls.parcel').write(cr, uid, child_id, {'status': 'Closed'}, context=context)



				#print "PROGRAM OK"

		except:
			#print "Fatal: Error writing xml/pdf file to disk!"
			return False

		return True

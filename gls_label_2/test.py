"""
class StockPickingPackagePreparation(models.Model):

	_inherit = 'stock.picking.package.preparation'

	gls_parcel = fields.One2many('gls.parcel', 'invoice_id', string="GLS parcel")
	label_binary = fields.Binary(string="GLS label binary")
	label_filename = fields.Char(string="GLS label")
	transportation_note = fields.Text(string="Transportation note")
	gls_config_id = fields.Many2one('gls.config', string="GLS contract")

	def gls_print(self, cr, uid, ids, context=None):
		_logger = logging.getLogger(__name__)
		for invoice in self.browse(cr, uid, ids, context=context):
			curr_invoice = invoice
		config = curr_invoice.gls_config_id or self.pool.get('gls.config').browse(cr, uid,1, context=context)
		if config.sedeID is None:
			raise except_orm("GLS Labeling", "COULD NOT GET CONFIG")

		colli = curr_invoice.parcels or 1
		progressive_counter = config.progressive_counter
		config.progressive_counter = progressive_counter

		if not curr_invoice.weight:
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


		invoice_name = curr_invoice.name
		if not invoice_name:
			raise except_orm("GLS Labeling", "This Ddt has no name!")
		invoice_name = invoice_name.replace("/", "-")
		client = curr_invoice.partner_id
		shipping_partner = curr_invoice.partner_shipping_id or client
		_logger.info("PARTNER %s " % shipping_partner)
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
				'provincia': shipping_partner.state_id.code,
				'peso_reale': vweight,
				'tipo_porto': tipo_porto,
				'cellulare1': shipping_partner.mobile or '',
				'email': shipping_partner.email or '',
				'extra_filename': invoice_name,
				'contatore_progressivo': progressive_counter,
				'colli': 1,
				'note': vnote,
				'invoice_id': curr_invoice.id,
				'config_id': config.id
			}
			counter = self.pool.get('gls.parcel').create(cr, uid, vals, context=context)
			prcls +=1
			if not counter:
				raise except_orm("GLS Labeling", "Fatal: Error creating parcel in local")


			print "CREATED GLS PARCEL LOCAL WITH ID: " + str(counter)
			#print vals

			parcel = self.pool.get('gls.parcel').browse(cr, uid, counter, context=context)[0]
			if not parcel:
				print "Parcel not retrieved"
				return False




			infostring = "<Info><SedeGls>" + config.sedeID+ "</SedeGls><CodiceClienteGls>"+config.glsUser+"</CodiceClienteGls><PasswordClienteGls>"+config.glsPass+"</PasswordClienteGls>"
			infostring += getInfoString(parcel, config.glsContract)
			infostring += "</Info>"
			if infostring is None:
				print "No infostring"
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
					print root.tag
					child = root[0]
					sped_num = child.find('NumeroSpedizione')
					if sped_num is None:
						print "Sped num not retrieved"
						return False
					if sped_num.text == '999999999':
						mess = child.find('NoteSpedizione')
						self.pool.get('gls.parcel').unlink(cr, uid, counter, context=None)
						raise osv.except_osv(_("GLS LABEL PRINT"), _(mess.text))


				#MAGENTO SHIPMENT
					magento_id = curr_invoice.magento_id
					mage_shipp_id = None
					if magento_id:

						_logger.warning("*****THIS ORDER IS IMPORTED FROM MAGENTO, INITIATING SHIPPING EXPORT PROCEDURE - %s ******" % magento_id)
						print "*****THIS ORDER IS IMPORTED FROM MAGENTO, INITIATING SHIPPING EXPORT PROCEDURE - %s ******" % magento_id
						inv_obj = curr_invoice
						items = []
						for item in inv_obj.source.order_line:

								print "******"
								print i.magento_id
								_logger.warning("**** %s" % i.magento_id)
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
									print "MAGENTO SHIPP ERROR"
									#raise except_orm("MAGENTO CONNECTOR", "SHIPPMENT CANNOT BE EXPORTED TO MAGENTO STORE")
				#END MAGENTO SHIPPMENT
					sigla = child.find('SiglaMittente')
					tot_colli = child.find('TotaleColli')
					t_collo = child.find('TipoCollo')
					dest = child.find('SiglaSedeDestino')
					date = child.find('DataSpedizione')
					comp_sped = "%s %s %s %s %s" % (sigla.text, sped_num.text, tot_colli.text, t_collo.text, dest.text)
					self.pool.get('gls.parcel').write(cr, uid, counter, {'date':date,'numero_spedizione': sped_num.text, 'name': comp_sped, 'status': 'Pending closure', 'magento_id': mage_shipp_id or 0}, context=context)
					print "SPED NUMBER: " + sped_num.text

					print child.tag
					label = child.find('PdfLabel')
					decoded = base64.b64decode(label.text)

					parcel.label_binary = label.text
					parcel.label_filename = "gls-%s.pdf" % invoice_name




					#label_name = '/home/testserver/odoo/ebay_temp/gls-%s.pdf' % invoice_name
					#swith open(label_name, 'w') as p:
					#	p.write(decoded)
					print "OK"
		#if prcls > 0:
		#	email_template = config.confirmation_email_template
		#	if email_template:
		#		self.pool.get('email.template').send_mail(cr, uid, email_template.id, curr_invoice.id)

"""

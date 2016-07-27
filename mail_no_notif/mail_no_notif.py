from openerp import fields, models, api, _
from datetime import datetime

class ResPartner(models.Model):
    _inherit = "res.partner"

    no_notifications = fields.Boolean(string="No notifications")

class MailNotification(models.Model):
    _inherit = "mail.notification"

    def get_partners_to_email(self, cr, uid, ids, message, context=None):
        res = super(MailNotification, self).get_partners_to_email(cr, uid, ids, message, context=context)
        print "IN GET PARTNERS"
        print len(res)
        for notification in self.browse(cr, uid, ids, context=context):
            print notification.type
            partner = notification.partner_id
            if partner.no_notifications:
                res.remove(partner.id)
                print partner.name

        print len(res)
        return res

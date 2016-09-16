from openerp import fields, models, api, _
import logging
from openerp.exceptions import ValidationError

NET_PRICE_TYPE = -4

class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    def _net_price_get(self):
        res = self._price_field_get()
        res.append((NET_PRICE_TYPE, _('Net price')))
        return res

    base = fields.Selection(
        selection='_net_price_get',
        string="Based on",
        size=-1,
        required=True,
        default=lambda self: self.default_get(fields_list=['base'])['base'],
        help="Base price for computation"
    )

    @api.constrains('base')
    def _check_net_price(self):
        if self.base == NET_PRICE_TYPE and not self.product_id:
            raise ValidationError(_('You must select product when using NET PRICE base'))

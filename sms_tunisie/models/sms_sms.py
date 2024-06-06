import re

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from ..tools.sms_api import ExtendedSmsApi


class SmsSms(models.Model):
    _inherit = "sms.sms"

    provider = fields.Selection(string='Provider', selection=[("sms_app_tunis", "Tunisie SMS"), ("odoo", "Odoo IAP")],
                                ondelete={"sms_app_tunis": "cascade"}, )

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if 'provider' in self.env.context:
            res.write({'provider': self.env.context.get("provider")})
        return res

    def _send(self, unlink_failed=False, unlink_sent=True, raise_exception=False):
        if self.provider == 'sms_app_tunis':
            if self.partner_id.country_id == self.env.ref('base.tn'):
                number = ''.join(re.findall(r'\d+', self.number))
                if len(number) == 11:
                    number = number[3:11]
                elif len(number) != 8:
                    raise UserError(_('The format phone number of %r is wrong', self.number))
            else:
                raise UserError(_('Tunisie SMS Work only in Tunisia'))
            return ExtendedSmsApi(self.env, self.body, number, self.create_date.strftime('%d/%m/%Y'),
                                  self.create_date.strftime('%H:%M:%S'))._send_sms_batch_sms_tunisie_http()
        else:
            return super()._send(unlink_failed=unlink_failed, unlink_sent=unlink_sent, raise_exception=raise_exception)

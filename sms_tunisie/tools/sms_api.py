import requests
from odoo.addons.sms.tools.sms_api import SmsApi
from odoo.exceptions import UserError



class ExtendedSmsApi(SmsApi):

    def __init__(self, env, body, number, date, time):
        super().__init__(env)
        self.env = env
        self.body = body
        self.number = number
        self.date = date
        self.time = time

    def _send_sms_batch_sms_tunisie_http(self):
        return self._contact_iap_sms_tunis_http()

    def _contact_iap_sms_tunis_http(self):
        account = self.env['iap.account'].search([('provider', '=', 'sms_app_tunis')], limit=1)


        if not account.sms_app_tunis_key or not account.sms_app_tunis_sender:
            raise UserError("Missing required SMS API credentials: key and/or sender")
        else:
            sms_url_tunisie = (
                    account.sms_app_tunis_endpoint + "?fct=sms&key=" + account.sms_app_tunis_key + "&sms=" + self.body +
                    "&mobile=216" + self.number + "&date=" + self.date + "&heure=" + self.time +
                    "&sender=" + account.sms_app_tunis_sender)
            return self._iap_send(sms_url_tunisie)

    def _iap_send(self, sms_url):
        return requests.post(sms_url)

from odoo import fields, models


class IapAccount(models.Model):
    _inherit = "iap.account"

    provider = fields.Selection(
        selection_add=[("sms_app_tunis", "Tunisie SMS")],
        ondelete={"sms_app_tunis": "cascade"},
    )

    sms_app_tunis_sender = fields.Char(string="Sender Name")
    sms_app_tunis_key = fields.Char(string="key")
    sms_app_tunis_endpoint = fields.Char(
        "Endpoint", default="https://www.tunisiesms.tn/client/Api/Api.aspx"
    )

    def _get_service_from_provider(self):
        if self.provider == "sms_app_tunis":
            return "sms"

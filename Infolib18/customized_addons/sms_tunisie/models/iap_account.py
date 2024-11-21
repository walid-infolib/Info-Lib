from odoo import fields, models, api


class IapAccount(models.Model):
    _inherit = "iap.account"

    provider = fields.Selection(
        selection=[
            ("odoo", "Odoo IAP"),
            ("sms_app_tunis", "Tunisie SMS")
        ],
        required=True,
        default="odoo",
    )

    sms_app_tunis_sender = fields.Char(string="Sender Name")
    sms_app_tunis_key = fields.Char(string="key")
    sms_app_tunis_endpoint = fields.Char('Endpoint', default='https://www.tunisiesms.tn/client/Api/Api.aspx')

    def _get_service_from_provider(self):
        if self.provider == "sms_app_tunis":
            return "sms"
        elif self.provider == "odoo":
            return None

    def _set_service_from_provider(self):
        for record in self:
            service = record._get_service_from_provider()
            if service and record.service_name != service:
                record.service_name = service

    @api.model_create_multi
    def create(self, vals_list):
        record = super().create(vals_list)
        record._set_service_from_provider()
        return record

    def write(self, vals):
        super().write(vals)
        self._set_service_from_provider()
        return True
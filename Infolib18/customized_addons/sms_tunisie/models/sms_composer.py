from odoo import models, fields


class SendSMS(models.TransientModel):
    _inherit = "sms.composer"

    provider = fields.Selection(
        string='Provider',
        selection=[("sms_app_tunis", "Tunisie SMS"), ("odoo", "Odoo IAP")],
        ondelete={
            "sms_app_tunis": "cascade"
        },
    )

    def action_send_sms(self):
        return super(SendSMS, self.with_context(provider=self.provider)).action_send_sms()


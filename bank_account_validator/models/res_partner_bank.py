from schwifty import IBAN
from schwifty.exceptions import SchwiftyException

from odoo import _, api, models
from odoo.exceptions import UserError


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    @api.constrains("acc_number")
    def check_acc_number(self):
        for account in self:
            try:
                iban = IBAN(account.acc_number)
            except SchwiftyException as e:
                raise UserError(_(e)) from None
            if not iban.is_valid:
                raise UserError(_("The Account Number is not valid."))

from schwifty import BIC
from schwifty.exceptions import SchwiftyException

from odoo import _, api, models
from odoo.exceptions import UserError


class ResBank(models.Model):
    _inherit = "res.bank"

    @api.constrains("bic")
    def check_bic(self):
        for bank in self:
            try:
                BIC(bank.bic)
            except SchwiftyException as e:
                raise UserError(_(e)) from None

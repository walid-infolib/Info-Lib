from odoo import models, api, _
from odoo.exceptions import UserError
from schwifty import BIC
from schwifty.exceptions import SchwiftyException


class ResBank(models.Model):
    _inherit = 'res.bank'

    @api.constrains('bic')
    def check_bic(self):
        for bank in self:
            try:
                BIC(bank.bic)
            except SchwiftyException as e:
                raise UserError(_(e))

import re

from odoo import _, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    def check_vat_tn(self, vat):
        res = super().check_vat_tn(vat=vat)
        pattern = r"^[A-Za-z0-9]{8}/[A,B,P,a,b,p]/[C,M,P,N,c,m,p,n]/[0-9]{3}$"
        if not re.match(pattern, self.vat):
            raise UserError(
                _(
                    "Error ! %r VAT number must respect this nomenclature (exp: 1234567Y/A/M/000)",
                    self.name,
                )
            )
        return res

from odoo import models
from odoo.addons.base_vat.models.res_partner import _ref_vat

_ref_vat["tn"] = "TN 1234567ABC000"

character_vat = {
    1: "a",
    2: "b",
    3: "c",
    4: "d",
    5: "e",
    6: "f",
    7: "g",
    8: "h",
    9: "j",
    10: "k",
    11: "l",
    12: "m",
    13: "n",
    14: "p",
    15: "q",
    16: "r",
    17: "s",
    18: "t",
    19: "v",
    20: "w",
    21: "x",
    22: "y",
    23: "z",
}


class ResPartner(models.Model):
    _inherit = "res.partner"

    def check_vat_tn(self, vat):
        """
        Check Tunisian VAT number.
        :param vat: partner VAT number
        :return: True or False
        """
        total = 0
        x = 7
        try:
            for n in vat[:7]:
                total += int(n) * x
                x -= 1
            residue = (total % 23) + 1
            if vat[7:8].upper() == character_vat[residue].upper():
                return True
            else:
                return False
        except ValueError:
            return False

from countryinfo import CountryInfo

from odoo import _, models
from odoo.exceptions import UserError


class ResCountry(models.Model):
    _inherit = "res.country"

    def get_provinces(self):
        self.ensure_one()
        country = CountryInfo(self.with_context(lang="en").name)
        try:
            provinces = country.provinces()
        except KeyError:
            raise UserError(_("Country not found.")) from None
        padding = len(str(len(provinces)))
        code = 1
        if padding:
            self.state_ids.unlink()
        for province in provinces:
            self.state_ids.create(
                {
                    "name": province,
                    "code": str(code).zfill(padding),
                    "country_id": self.id,
                }
            )
            code += 1

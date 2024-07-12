from validate_email import validate_email
from odoo import models, _, api
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.constrains("email")
    def check_email(self):
        for partner in self:
            if partner.email:
                if not validate_email(partner.email, verify=True):
                    raise UserError(_("The %s Email is Invalid.") % partner.email)

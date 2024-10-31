from odoo import fields, models


class Partner(models.Model):
    _inherit = "res.partner"

    stamp_tax_partner = fields.Boolean("Tax Stamp", default=False)

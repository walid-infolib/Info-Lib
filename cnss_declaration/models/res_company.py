from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    ssnid = fields.Char(string="SSN No", help="Social Security Number")
    br = fields.Char(string="Office Number", help="Office Number")
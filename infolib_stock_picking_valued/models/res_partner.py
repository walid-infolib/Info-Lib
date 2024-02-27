from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    delivery_report_valued = fields.Boolean(string="Value the delivery note", default=False)

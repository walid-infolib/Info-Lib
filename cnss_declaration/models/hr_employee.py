from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    pro_category = fields.Char(
        string="Professional category", help="Professional category"
    )

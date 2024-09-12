from odoo import models, fields, api


class Employee(models.Model):
    _inherit = 'hr.employee'

    agreement_ids = fields.One2many("hr.employee.agreement", "employee_id", string="Collective agreement history")
    head_of_the_family = fields.Boolean(string='Head of the family', default=False, help="Chef de famille")


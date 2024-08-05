from odoo import models, fields, api


class Employee(models.Model):
    _inherit = 'hr.employee'

    agreement_ids = fields.One2many("hr.employee.agreement", "employee_id", string="Collective agreement history")


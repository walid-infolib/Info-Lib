from odoo import models, fields


class HrPayrollStructureType(models.Model):
    _inherit = 'hr.payroll.structure.type'

    default_work_entry_days = fields.Float(
        string="Default number of days per month",
    )
    default_work_entry_hours = fields.Float(
        string="Default number of hours per month",
    )
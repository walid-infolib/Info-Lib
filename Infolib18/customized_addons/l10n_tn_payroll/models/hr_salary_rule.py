from odoo import models, fields


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    appears_on_payslip_quantity = fields.Boolean(string='Appears on Payslip Quantity', default=False,
        help="Used to display the Quantity on payslip Report.")


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    appears_on_payslip_quantity = fields.Boolean(string='Appears on Payslip Quantity', related="salary_rule_id.appears_on_payslip_quantity")


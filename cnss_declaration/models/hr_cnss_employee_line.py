from odoo import fields, models


class HrCnssEmployeeLine(models.Model):
    _name = "hr.cnss.line"
    _description = "cnss line"
    _order = "registration_number desc"

    cnss_id = fields.Many2one("hr.cnss", ondelete="cascade")
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True)
    ssnid = fields.Char(
        related="employee_id.ssnid",
        string="SSN No",
        help="Social Security Number",
        store=True,
    )
    registration_number = fields.Char(
        related="employee_id.registration_number", store=True
    )
    pro_category = fields.Char(
        related="employee_id.pro_category",
        string="Professional category",
        help="Professional category",
        store=True,
    )
    page = fields.Integer(string="page")
    line = fields.Integer(string="line")
    gross_1 = fields.Monetary(string="gross month 1")
    gross_2 = fields.Monetary(string="gross month 2")
    gross_3 = fields.Monetary(string="gross month 3")
    total = fields.Monetary(string="Total")
    company_id = fields.Many2one(
        related="cnss_id.company_id", store=True, index=True, precompute=True
    )
    currency_id = fields.Many2one(
        related="cnss_id.currency_id",
        depends=["cnss_id.currency_id"],
        store=True,
        precompute=True,
    )

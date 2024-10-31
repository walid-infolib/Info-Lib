from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class CollectiveAgreement(models.Model):
    _name = "collective.agreement"
    _description = "Collective Agreement"

    name = fields.Char(string="Name", required=True)
    date_effective = fields.Date(string="Effective Date", required=True)
    description = fields.Text(string="Description")
    category_ids = fields.One2many(
        "collective.category", "agreement_id", string="Categories"
    )


class Category(models.Model):
    _name = "collective.category"
    _description = "Category"

    name = fields.Char(string="Category", required=True)
    display_name = fields.Char(compute="_compute_display_name")
    agreement_id = fields.Many2one(
        "collective.agreement", string="Agreement", required=True
    )
    level_ids = fields.One2many("collective.level", "category_id", string="Levels")

    @api.depends("name", "agreement_id")
    def _compute_display_name(self):
        for category in self:
            category.display_name = (
                category.name + " (" + category.agreement_id.name + ")"
            )


class Level(models.Model):
    _name = "collective.level"
    _description = "Level"

    name = fields.Integer(string="Level", required=True)
    display_name = fields.Char(compute="_compute_display_name")
    agreement_id = fields.Many2one(
        "collective.agreement",
        string="Agreement",
        related="category_id.agreement_id",
        store=True,
    )
    category_id = fields.Many2one(
        "collective.category", string="Category", required=True
    )
    seniority = fields.Integer(string="Seniority (years)", required=True, default=2)
    salary = fields.Float(string="Salary", required=True, digits="Payroll")

    @api.depends("name", "category_id.name")
    def _compute_display_name(self):
        for level in self:
            level.display_name = "C " + level.category_id.name + " E " + str(level.name)


class EmployeeAgreement(models.Model):
    _name = "hr.employee.agreement"
    _description = "Collective agreement history"
    _order = "date_start, employee_id"

    employee_id = fields.Many2one(
        "hr.employee", "Employee", required=True, ondelete="restrict"
    )
    level_id = fields.Many2one(
        "collective.level", "Agreement", required=True, ondelete="restrict"
    )
    date_start = fields.Date("Date Start")
    date_end = fields.Date("Date End", compute="_compute_date_end", store=True)

    @api.depends("date_start", "level_id")
    def _compute_date_end(self):
        for line in self:
            if line.level_id:
                line.date_end = line.date_start + relativedelta(
                    years=line.level_id.seniority
                )
            else:
                line.date_end = False

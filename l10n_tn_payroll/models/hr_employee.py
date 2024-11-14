from odoo import api, fields, models


class Employee(models.Model):
    _inherit = "hr.employee"

    agreement_ids = fields.One2many(
        "hr.employee.agreement", "employee_id", string="Collective agreement history"
    )
    head_of_the_family = fields.Boolean(
        string="Head of the family", default=False, help="Head of the family"
    )
    parent_in_charge = fields.Selection(
        [("1", "1"), ("2", "2")], string="Parent in charge", help="Parent in charge"
    )
    disabled_child = fields.Integer(
        string="Disabled Child", default=False, help="Disabled Child"
    )
    student = fields.Integer(
        string="Number of children studying",
        default=False,
        help="A child pursuing higher education "
        "without a grant and under the age of 25, within "
        "the limits of the first four children",
    )

    allocation_display = fields.Char(
        string="Total Allocations", compute="_compute_new_fields"
    )

    @api.depends("allocation_display", "allocation_remaining_display")
    def _compute_new_fields(self):
        for record in self:
            record.allocation_display = f"{record.allocation_remaining_display} / {record.allocation_display} Days"

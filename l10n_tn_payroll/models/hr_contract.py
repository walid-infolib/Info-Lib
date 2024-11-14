from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = "hr.contract"

    agreement_id = fields.Many2one(
        comodel_name="collective.level",
        string="Agreement",
        compute="_compute_agreement_id",
        inverse="_inverse_agreement_id",
    )
    payment_type = fields.Selection(
        [("cash", "Cash"), ("bank_transfer", "Bank transfer")],
        string="Payment Type",
        help="Payment Type",
    )

    @api.depends("employee_id")
    def _compute_agreement_id(self):
        for contract in self:
            contract.agreement_id = (
                self.env["hr.employee.agreement"]
                .search(
                    [("employee_id", "=", contract.employee_id.id)],
                    limit=1,
                    order="date_end DESC",
                )
                .level_id
            )

    def _inverse_agreement_id(self):
        for contract in self:
            if contract.agreement_id:
                self.env["hr.employee.agreement"].create(
                    {
                        "employee_id": contract.employee_id.id,
                        "level_id": contract.agreement_id.id,
                        "date_start": fields.Date.today(),
                    }
                )

    @api.onchange("agreement_id")
    def _onchange_agreement_id(self):
        self.wage = self.agreement_id.salary

from odoo import api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    withholding_tax_id = fields.Many2one("withholding.tax", string="Withholding tax")
    withholding_journal_id = fields.Many2one(
        "account.journal", string="Withholding journal"
    )

    withholding_amount = fields.Monetary("Withholding tax amount")
    amount_net = fields.Monetary("Withholding tax net")

    @api.onchange("withholding_tax_id")
    def _onchange_withholding_tax(self):
        for record in self:
            if record.amount_net == 0:
                record.amount_net = record.amount
            record.amount = record.amount_net * (
                1 - record.withholding_tax_id.amount / 100
            )
            record.withholding_amount = (
                record.amount_net * record.withholding_tax_id.amount / 100
            )

    @api.onchange("amount_net")
    def _onchange_amount_net(self):
        for record in self:
            record.withholding_amount = (
                record.amount_net * record.withholding_tax_id.amount / 100
            )
            record.amount = record.amount_net * (
                1 - record.withholding_tax_id.amount / 100
            )

    @api.onchange("withholding_amount")
    def _onchange_withholding_amount(self):
        for record in self:
            record.amount = record.amount_net - record.withholding_amount

    @api.onchange("amount")
    def _onchange_amount(self):
        for record in self:
            record.withholding_amount = record.amount_net - record.amount

    @api.model
    def _get_line_batch_key(self, line):
        res = super()._get_line_batch_key(line=line)
        res["withholding_tax_id"] = self.withholding_tax_id.id
        res["withholding_journal_id"] = self.withholding_journal_id.id
        res["withholding_amount"] = self.withholding_amount
        res["amount_net"] = self.amount_net
        return res

    def _create_payment_vals_from_wizard(self, batch_result):
        res = super()._create_payment_vals_from_wizard(batch_result=batch_result)
        res["withholding_tax_id"] = batch_result["payment_values"]["withholding_tax_id"]
        res["withholding_journal_id"] = batch_result["payment_values"][
            "withholding_journal_id"
        ]
        res["withholding_amount"] = batch_result["payment_values"]["withholding_amount"]
        res["amount_net"] = batch_result["payment_values"]["amount_net"]
        return res

    def _create_payment_vals_from_batch(self, batch_result):
        res = super()._create_payment_vals_from_batch(batch_result=batch_result)
        res["withholding_tax_id"] = self.withholding_tax_id.id
        res["withholding_journal_id"] = self.withholding_journal_id.id
        res["withholding_amount"] = res["amount"] * (
            self.withholding_tax_id.amount / 100
        )
        res["amount_net"] = res["amount"]
        res["amount"] = res["amount"] * (1 - (self.withholding_tax_id.amount / 100))
        return res

    def _create_payments(self):
        res = super()._create_payments()
        domain = [
            ("parent_state", "=", "posted"),
            (
                "account_type",
                "in",
                self.env["account.payment"]._get_valid_payment_account_types(),
            ),
        ]
        for payment in self:
            payment_lines = (
                payment.line_ids.filtered_domain(domain)
                + res.withholding_move_id.line_ids.filtered_domain(domain)
                + res.line_ids.filtered_domain(domain)
            )
            for account in payment_lines.account_id:
                if self.group_payment:
                    payment_lines.filtered_domain(
                        [("account_id", "=", account.id), ("reconciled", "=", True)]
                    ).remove_move_reconcile()

                    payment_lines.filtered_domain(
                        [("account_id", "=", account.id), ("reconciled", "=", False)]
                    ).reconcile()
                else:
                    for pay in res:
                        payment_lines = (
                            pay.withholding_move_id.line_ids.filtered_domain(domain)
                            + pay.line_ids.filtered_domain(domain)
                            + pay.reconciled_invoice_ids.line_ids.filtered_domain(
                                domain
                            )
                            + pay.reconciled_bill_ids.line_ids.filtered_domain(domain)
                        )
                        payment_lines.filtered_domain(
                            [("account_id", "=", account.id), ("reconciled", "=", True)]
                        ).remove_move_reconcile()
                        payment_lines.filtered_domain(
                            [
                                ("account_id", "=", account.id),
                                ("reconciled", "=", False),
                            ]
                        ).reconcile()
        return res

    @api.depends("can_edit_wizard", "amount")
    def _compute_payment_difference(self):
        for wizard in self:
            if not wizard.withholding_tax_id:
                super(AccountPaymentRegister, wizard)._compute_payment_difference()
            elif wizard.can_edit_wizard and wizard.payment_date:
                batch_result = wizard._get_batches()[0]
                total_amount_residual_in_wizard_currency = (
                    wizard._get_total_amount_in_wizard_currency_to_full_reconcile(
                        batch_result, early_payment_discount=False
                    )[0]
                )
                wizard.payment_difference = (
                    total_amount_residual_in_wizard_currency - wizard.amount_net
                )
            else:
                wizard.payment_difference = 0.0

from odoo import api, fields, models, _


class AccountPayment(models.Model):
    _inherit = "account.payment"

    withholding_tax_id = fields.Many2one("withholding.tax", string="Withholding tax")
    withholding_journal_id = fields.Many2one("account.journal", string="Withholding journal")

    withholding_amount = fields.Monetary("Withholding tax amount")
    amount_net = fields.Monetary("Withholding tax net")
    withholding_move_id = fields.Many2one("account.move", 'Withholding move')

    @api.onchange("withholding_tax_id")
    def _onchange_withholding_tax(self):
        for record in self:
            if record.amount_net == 0:
                record.amount_net = record.amount
            record.amount = record.amount_net * (1 - record.withholding_tax_id.amount / 100)
            record.withholding_amount = record.amount_net * record.withholding_tax_id.amount / 100

    @api.onchange("amount_net")
    def _onchange_amount_net(self):
        for record in self:
            record.withholding_amount = record.amount_net * record.withholding_tax_id.amount / 100
            record.amount = record.amount_net * (1 - record.withholding_tax_id.amount / 100)

    @api.onchange("withholding_amount")
    def _onchange_withholding_amount(self):
        for record in self:
            record.amount = record.amount_net - record.withholding_amount

    @api.onchange("amount")
    def _onchange_amount(self):
        for record in self:
            if record.amount != record.amount_net - record.withholding_amount:
                record.amount_net = record.amount
                record.withholding_amount = record.amount_net - record.amount
            else:
                record.withholding_amount = record.amount_net - record.amount

    def button_open_journal_entry_withholding(self):
        ''' Redirect the user to this payment journal.
        :return:    An action on account.move.
        '''
        self.ensure_one()
        return {
            'name': _("Journal Entry"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
            'view_mode': 'form',
            'res_id': self.withholding_move_id.id,
        }

    def _prepare_account_move_line(self):
        self.ensure_one()
        description = _("Wihholding Tax %s - %s - %s") % (self.withholding_amount, self.partner_id.name, str(self.date))
        partner_id = self.partner_id.id
        amount = self.currency_id._convert(self.withholding_amount, self.company_currency_id, self.company_id,
                                           self.date)
        if self.payment_type == "inbound":
            credit_account_id = self.partner_id.property_account_receivable_id.id
            debit_account_id = self.withholding_tax_id.account_customer_id.id
        else:
            credit_account_id = self.withholding_tax_id.account_supplier_id.id
            debit_account_id = self.partner_id.property_account_payable_id.id

        res = [(0, 0, {
            'name': description,
            'ref': description,
            'partner_id': partner_id,
            'credit': amount,
            'account_id': credit_account_id,
        }),
               (0, 0, {
                   'name': description,
                   'ref': description,
                   'partner_id': partner_id,
                   'debit': amount,
                   'account_id': debit_account_id,
               })
               ]
        return res

    def action_post(self):
        res = super().action_post()
        for payment in self:
            if payment.withholding_tax_id:
                payment.withholding_move_id = self.env['account.move'].sudo().create({
                    'journal_id': payment.withholding_journal_id.id,
                    'line_ids': payment._prepare_account_move_line(),
                    'date': payment.date,
                    'ref': payment.ref,
                    'move_type': 'entry',
                })
                if payment.withholding_move_id.state == 'draft':
                    payment.withholding_move_id._post()
        return res

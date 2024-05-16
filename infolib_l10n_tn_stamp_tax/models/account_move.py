from odoo import models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.move_type == 'out_invoice':
            tfs = self.env['ir.model.data'].search([('name', 'ilike', 'l10n_tn_tax_vat_sale_tax_stamp')])
            stamp_tax = self.env["account.tax"].browse(tfs.res_id)
        elif self.move_type == 'in_invoice':
            tfp = self.env['ir.model.data'].search([('name', 'ilike', 'l10n_tn_tax_vat_purchase_tax_stamp')])
            stamp_tax = self.env["account.tax"].browse(tfp.res_id)
        else:
            return

        existing_stamp_tax_line = self.invoice_line_ids.filtered(
            lambda line: stamp_tax.id in line.tax_ids.ids
        )

        if self.partner_id.stamp_tax_partner:
            if not existing_stamp_tax_line:
                self.invoice_line_ids += self.env['account.move.line'].new({
                    'price_unit': 0,
                    'tax_ids': [(6, 0, [stamp_tax.id])],

                })
        else:
            if existing_stamp_tax_line:
                self.invoice_line_ids -= existing_stamp_tax_line

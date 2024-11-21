from odoo import models


class AccountGenericTaxReport(models.AbstractModel):
    _inherit = 'account.generic.tax.report'

    def _l10n_be_reports_get_deduction_text(self, options):
        deduction_dict = options.get('prorata_deduction', {})
        if not deduction_dict.get('prorata'):
            return ''

        return self.env['ir.qweb']._render('l10n_be_reports_prorata.vat_export_prorata', deduction_dict)

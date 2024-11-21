# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import base64

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, RedirectWarning


class AccountGeneralLedger(models.AbstractModel):
    _inherit = 'account.general.ledger'

    def _get_reports_buttons(self, options):
        # OVERRIDE
        buttons = super()._get_reports_buttons(options)
        if self.env.company.account_fiscal_country_id.code == 'NO':
            buttons.append({'name': _('SAF-T'), 'sequence': 5, 'action': 'print_xml', 'file_export_type': _('XML')})
        return buttons

    def _get_saft_report_template(self):
        # OVERRIDE account_saft/models/account_general_ledger
        if self.env.company.account_fiscal_country_id.code != 'NO':
            return super()._get_saft_report_template()
        return self.env.ref('l10n_no_saft.saft_template_inherit_l10n_no_saft')

    @api.model
    def _prepare_saft_report_values(self, options):
        # OVERRIDE
        is_NO = self.env.company.country_code == 'NO'
        options['saft_allow_empty_address'] = is_NO
        template_vals = super()._prepare_saft_report_values(options)
        if not is_NO:
            return template_vals

        if not self.env.ref('l10n_no_saft.balance_account', raise_if_not_found=False):
            # The update to SAF-T 1.30 changed and added some templates. The module needs to be upgraded if those templates are not found
            raise RedirectWarning(
                message=_("The version for the SAF-T file has been updated. Please upgrade its module (l10n_no_saft) for the export to work properly."),
                action=self.env.ref('base.open_module_tree').id,
                button_text=_("Go to Apps"),
                additional_context={
                    'search_default_name': 'l10n_no_saft',
                    'search_default_extra': True,
                },
            )

        # The Norwegian version of the SAF-T asks for a standard tax code to be given. This code is only present in the name
        # or description (depending on the Odoo version) of the tax. The code, as set in Odoo, is the first digit in the name or description.
        # If no code is found, we set it to a default non-existant '02' tax code, as it was done since Odoo 13.
        # TODO Create a dedicated field for the standard tax code for Norwegian loca in master and change the error to "description" in later versions
        for tax_vals in template_vals['tax_vals_list']:
            for word in tax_vals['name'].split(' '):
                if word.isdigit():
                    tax_vals['standard_code'] = int(word)
                    break
            if not tax_vals.get('standard_code'):
                raise UserError(_("Please change your tax names to include their Norwegian standard tax code, delimited by spaces.\n"
                    "For example: 'Utgående mva lav sats 12%' => '33 Utgående mva lav sats 12%'"))

        # The Norwegian version of the SAF-T requires account code to be provided along with the opening/closing
        # credit/debit of customers and suppliers
        accounts_by_partners = self._get_partners_accounts(options)

        for partner_vals in template_vals['customer_vals_list'] + template_vals['supplier_vals_list']:
            partner_id = partner_vals['partner'].id
            if partner_id in accounts_by_partners:
                partner_vals['accounts'] = list(accounts_by_partners[partner_id].values())

        template_vals.update({
            'xmlns': 'urn:StandardAuditFile-Taxation-Financial:NO',
            'file_version': '1.30',
            'accounting_basis': 'A',
        })
        return template_vals

    @api.model
    def get_xml(self, options):
        # OVERRIDE
        content = super().get_xml(options)

        if self.env.company.account_fiscal_country_id.code != 'NO':
            return content

        xsd_attachment = self.env['ir.attachment'].search([('name', '=', 'xsd_cached_Norwegian_SAF-T_Financial_Schema_v_1.30_xsd')])
        if xsd_attachment:
            with io.BytesIO(base64.b64decode(xsd_attachment.with_context(bin_size=False).datas)) as xsd:
                tools.xml_utils._check_with_xsd(content, xsd)
        return content

    def _get_partners_accounts(self, options):
        """Retrieve the accounts used for transactions with the different partners (customer/supplier).

        The Norwegian regulation (based on xsd file) requires a list of accounts for every partner, with starting and closing balances.
        The partner ledger in Odoo provides starting and closing balance for every partner, but it is account insensitive.
        So it is needed to fetch account lines in order to compute all of this, on account/partner basis.
        This is based on the Lithuanian method of the same name (next SAF-T needing this might do it in account_saft directly).

        :rtype: dict
        :return: dictionary of partners' accounts with the account code and its opening/closing balance
        """
        date_from = fields.Date.to_date(options['date']['date_from'])
        date_to = fields.Date.to_date(options['date']['date_to'])
        modified_options = options.copy()
        # Fetch data from beginning
        modified_options['date']['date_from'] = False
        tables, where_clause, where_params = self._query_get(modified_options)
        # The balance dating from earlier periods are computed as opening
        # The balance up to the end of the current period are computed as closing
        self._cr.execute(f'''
            SELECT DISTINCT
                account_move_line.partner_id,
                account.code,
                CASE WHEN account_move_line.date < '{date_from}' THEN SUM(account_move_line.balance) ELSE 0 END AS opening_balance,
                CASE WHEN account_move_line.date <= '{date_to}'  THEN SUM(account_move_line.balance) ELSE 0 END AS closing_balance
            FROM {tables}
            JOIN account_account account ON account.id = account_move_line.account_id
            WHERE {where_clause}
            AND account.internal_type IN ('receivable', 'payable')
            GROUP BY account_move_line.partner_id, account.code, account_move_line.date
        ''', where_params)

        partners_accounts = {}
        for vals in self._cr.dictfetchall():
            partner_id = vals['partner_id']
            account_code = vals['code']
            partner_account_code_balances = partners_accounts.setdefault(partner_id, {}).setdefault(account_code, {
                'code': account_code,
                'opening_balance': 0,
                'closing_balance': 0,
            })
            partner_account_code_balances['opening_balance'] += vals['opening_balance']
            partner_account_code_balances['closing_balance'] += vals['closing_balance']

        return partners_accounts

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.addons.l10n_eu_oss.models.eu_tax_map import EU_TAX_MAP
from odoo.exceptions import UserError

from collections import defaultdict
from lxml import etree, objectify
from dateutil.relativedelta import relativedelta

class AccountGenericTaxReport(models.AbstractModel):
    _inherit = 'account.generic.tax.report'

    def _init_filter_tax_report(self, options, previous_options=None):
        # Overridden to accept generic_oss_no_import and generic_oss_import reports as well
        super()._init_filter_tax_report(options, previous_options=previous_options)

        company_ids = [company_opt['id'] for company_opt in options.get('multi_company', [])] or self.env.company.ids
        oss_tag = self.env.ref('l10n_eu_oss.tag_oss')
        oss_rep_ln = self.env['account.tax.repartition.line']\
                     .search([('tag_ids', 'in', oss_tag.ids), ('company_id', 'in', company_ids)], limit=1)

        options['available_oss_reports'] = ['generic_oss_import', 'generic_oss_no_import'] if oss_rep_ln else []

        previous_options_report = (previous_options or {}).get('tax_report')
        if previous_options_report in {'generic_oss_import', 'generic_oss_no_import'}:
            options['tax_report'] = previous_options_report if previous_options_report in options['available_oss_reports'] else 'generic'

    @api.model
    def _get_options_domain(self, options):
        domain = super()._get_options_domain(options)

        if options['tax_report'] == 'generic_oss_no_import':
            domain += [
                ('tax_tag_ids', 'in', self.env.ref('l10n_eu_oss.tag_oss').ids),
                ('tax_tag_ids', 'not in', self.env.ref('l10n_eu_oss.tag_eu_import').ids),
            ]

        elif options['tax_report'] == 'generic_oss_import':
            domain += [
                ('tax_tag_ids', 'in', self.env.ref('l10n_eu_oss.tag_oss').ids),
                ('tax_tag_ids', 'in', self.env.ref('l10n_eu_oss.tag_eu_import').ids),
            ]

        return domain

    @api.model
    def _get_lines(self, options, line_id=None):
        rslt = super()._get_lines(options, line_id=line_id)

        if options['tax_report'] in {'generic_oss_import', 'generic_oss_no_import'}:
            rslt = self._process_generic_lines_for_oss_report(rslt)

        return rslt

    @api.model
    def _process_generic_lines_for_oss_report(self, generic_lines):
        """ The country for OSS taxes can't easily be guessed from SQL, as it would create JOIN issues.
        So, instead of handling them as a grouping key in the tax report engine, we
        post process the result of a grouping made by (type_tax_use, id) to inject the
        grouping by country.

        :param generic_lines: The result of super()._get_lines for a grouping by (type_tax_use, id)

        :param: the lines for the OSS reports, grouped by (type_tax_use, OSS country, id)
        """
        def append_country_and_taxes_lines(rslt, tax_lines_by_country):
            for country, tax_lines in sorted(tax_lines_by_country.items(), key=lambda elem: elem[0].display_name):
                col_number = len(tax_lines[0]['columns']) if tax_lines else 0
                tax_sums = [
                    sum(tax_lines[line_index]['columns'][col_index]['no_format'] for line_index in range(len(tax_lines)))
                    for col_index in range(1, col_number, 2)
                ]

                country_columns = []
                for tax_sum in tax_sums:
                    country_columns += [{'name': ''}, {'no_format': tax_sum, 'name': self.format_value(tax_sum)}]

                country_line = {
                    'id': self._get_generic_line_id('res.country', country.id, parent_line_id=line['id']),
                    'name': country.display_name,
                    'columns': country_columns,
                    'unfoldable': False,
                    'level': 2,
                }

                rslt.append(country_line)

                for tax_line in tax_lines:
                    tax_parsed_id = self._parse_line_id(tax_line['id'])[-1]
                    tax_line['level'] = 3
                    tax_line['id'] = self._get_generic_line_id(
                        markup=tax_parsed_id[0],
                        model_name=tax_parsed_id[1],
                        value=tax_parsed_id[2],
                        parent_line_id=line['id']
                    )
                    rslt.append(tax_line)

        rslt = []
        tax_lines_by_country = defaultdict(lambda: [])
        for line in generic_lines:
            model_info = self._get_model_info_from_id(line['id'])
            if model_info[0] != 'account.tax':
                # Then it's a type_tax_use_section
                # If there were tax lines for the previous section, append them to rslt; the previous section is over
                append_country_and_taxes_lines(rslt, tax_lines_by_country)

                # Start next section
                rslt.append(line)
                tax_lines_by_country = defaultdict(lambda: [])

            else:
                # line is a tax line
                tax = self.env['account.tax'].browse(model_info[1])
                tax_oss_country = self.env['account.fiscal.position.tax'].search([('tax_dest_id', '=', tax.id)])\
                                                                         .mapped('position_id.country_id')

                if not tax_oss_country:
                    raise UserError(_("OSS tax %s is not mapped in any fiscal position with a country set.", tax.display_name))
                elif len(tax_oss_country) > 1:
                    raise UserError(_("Inconsistent setup: OSS tax %s is mapped in fiscal positions from different countries.", tax.display_name))

                tax_lines_by_country[tax_oss_country].append(line)

        # Append the tax and country lines for the last section
        append_country_and_taxes_lines(rslt, tax_lines_by_country)

        return rslt

    def _get_reports_buttons(self, options):
        res = super()._get_reports_buttons(options)
        if options['tax_report'] in {'generic_oss_import', 'generic_oss_no_import'}:
            # Disable the tax closing for OSS reports: we currently don't support it. It has to be done manually.
            res = [button for button in res if button['action'] != 'periodic_vat_entries']

            # Add OSS XML export if there is one available for the domestic country
            if self._get_oss_xml_template(options):
                res.append({'name': _('XML'), 'sequence': 3, 'action': 'print_xml', 'file_export_type': _('XML')})
        return res

    def get_xml(self, options):
        if options['tax_report'] not in {'generic_oss_import', 'generic_oss_no_import'}:
            return super().get_xml(options)

        def get_period():
            """ Compute the values (Year, Quarter, Month) required for the 'Period' node.
            This node is used either at the XML root or inside the 'CorrectionsInfo' node.
            There are two possible cases for the latter:
                1. The total tax amount for the country is negative:
                --> We declare the corrections for the previous period.
                2. The country has at least one tax rate with a negative amount but its total is positive:
                --> We declare the corrections in the current period.
            """
            month = None
            quarter = None
            date_to = fields.Date.from_string(options['date']['date_to'])

            if options['date']['period_type'] == 'month':
                if previous_period:
                    date_to -= relativedelta(months=1)
                month = date_to.month
            elif options['date']['period_type'] == 'quarter':
                if previous_period:
                    date_to -= relativedelta(months=3)
                quarter = (int(date_to.month) - 1) // 3 + 1
            else:
                raise UserError(_('Choose a month or quarter to export the OSS report'))

            return date_to.year, quarter, month

        def get_line_data():
            year, quarter, month = get_period()
            return {
                'tax': tax,
                'net_amt': 0.0 if corrections_amount else line_net_amt,
                'tax_amt': 0.0 if corrections_amount else line_tax_amt,
                'corr_amt': corrections_amount,
                'corr_year': year,
                'corr_quarter': quarter,
                'corr_month': month,
                'currency': sender_company.currency_id,
                'supply_type': tax_scopes[tax.tax_scope].upper() if tax.tax_scope else 'GOODS',
                'rate_type': 'STANDARD' if tax.amount == eu_standard_rates[current_country.code] else 'REDUCED',
            }

        eu_countries = self.env.ref('base.europe').country_ids
        # prepare a dict of european standard tax rates {'AT': 20.0, 'BE': 21.0 ... }
        # sorted() is here needed to ensure the dict will contain the highest rate each time
        eu_standard_rates = {source_code: rate for source_code, rate, target_code in sorted(EU_TAX_MAP.keys())}
        tax_scopes = dict(self.env['account.tax'].fields_get()['tax_scope']['selection'])
        sender_company = self._get_sender_company_for_export(options)

        data = {}
        current_country = None
        corrections_amount = 0.0
        previous_period = False
        tax = None
        year, quarter, month = get_period()

        for line in filter(lambda x: x['columns'][1]['no_format'], self._get_lines(options)):
            model, model_id = self._get_model_info_from_id(line['id'])
            line_net_amt = line['columns'][0].get('no_format', 0.0)
            line_tax_amt = line['columns'][1].get('no_format', 0.0)

            if model == 'res.country':
                # If there are corrections (a.k.a. negative tax amounts) for the current country,
                # they are added at the end, right before the next country.
                # That is why the corrections amount is reset before moving on to the next country.
                if corrections_amount:
                    data[current_country].append(get_line_data())
                    corrections_amount = 0.0

                current_country = self.env['res.country'].browse(model_id)
                data[current_country] = []
                previous_period = line_tax_amt < 0.0

            elif model == 'account.tax':
                tax = self.env['account.tax'].browse(model_id)
                if line_tax_amt > 0.0:
                    data[current_country].append(get_line_data())
                else:
                    corrections_amount += line_tax_amt

        # If there are corrections for the last country,
        # they must be added here since we won't iterate through another country.
        if corrections_amount:
            data[current_country].append(get_line_data())

        values = {
            'VATNumber': sender_company.vat if sender_company.account_fiscal_country_id in eu_countries and sender_company.country_id != self.env.company.country_id else None,
            'VoesNumber': sender_company.voes if sender_company.account_fiscal_country_id not in eu_countries else None,
            'IOSSNumber': sender_company.ioss if options['tax_report'] == 'generic_oss_import' else None,
            'IntNumber': sender_company.intermediary_no if options['tax_report'] == 'generic_oss_import' else None,
            'PartnerVATNumber': self.env.company.vat,
            'Year': year,
            'Quarter': quarter,
            'Month': month,
            'country_taxes': data,
            'creation_timestamp': fields.Datetime.context_timestamp(self, fields.Datetime.now()),
        }

        export_template_ref = self._get_oss_xml_template(options)
        rendered_content = self.env.ref(export_template_ref)._render(values)
        tree = objectify.fromstring(rendered_content)
        return etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding='utf-8')

    def _get_oss_xml_template(self, options):
        ''' Used to get the template ref for XML export
        Override this method to include additional templates for other countries
        Also serves as a check to verify if the options selected are conducive to an XML export
        '''
        export_template_ref = False

        country_code = self._get_sender_company_for_export(options).account_fiscal_country_id.code
        if country_code == 'BE':
            export_template_ref = 'l10n_eu_oss_reports.eu_oss_generic_export_xml_be'
        elif country_code == 'LU':
            export_template_ref = 'l10n_eu_oss_reports.eu_oss_generic_export_xml_lu'

        return export_template_ref

    def _get_vat_closing_entry_additional_domain(self):
        # OVERRIDE
        domain = super()._get_vat_closing_entry_additional_domain()
        domain += [
            ('tax_tag_ids', 'not in', self.env.ref('l10n_eu_oss.tag_oss').ids),
        ]
        return domain

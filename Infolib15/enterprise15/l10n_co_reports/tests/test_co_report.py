from freezegun import freeze_time

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged
from odoo import fields, Command


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nCoReports(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_co.l10n_co_chart_template_generic'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.test_account = cls.env['account.account'].create({
            'name': 'Test Account',
            'code': '24080000',
            'user_type_id': cls.env.ref('account.data_account_type_current_liabilities').id,
            'reconcile': False,
            'company_id': cls.company_data['company'].id,
        })
        cls.test_tax_account = cls.env['account.account'].create({
            'name': 'Test Tax Account',
            'code': '23670000',
            'user_type_id': cls.env.ref('account.data_account_type_current_liabilities').id,
            'reconcile': False,
            'company_id': cls.company_data['company'].id,
        })
        cls.iva_purchase_tax = cls.env['account.tax'].create({
            'name': 'Tax 19% IVA',
            'amount_type': 'percent',
            'amount': 19,
            'type_tax_use': 'purchase',
            'invoice_repartition_line_ids': [
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'account_id': cls.test_account.id,
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'account_id': cls.test_account.id,
                }),
            ],
        })
        cls.rte_iva_15_over_19_purchase_tax = cls.env['account.tax'].create({
            'name': 'Withholding 15% over 19% IVA Tax',
            'amount_type': 'percent',
            'amount': -2.85,
            'type_tax_use': 'purchase',
            'invoice_repartition_line_ids': [
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'account_id': cls.test_tax_account.id,
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'account_id': cls.test_tax_account.id,
                }),
            ],
        })

    @freeze_time('2017-01-01')
    def test_balance_report_iva(self):
        """Test lines without tax base amount are correctly filtered out.
           Only lines with a withholding tax should appear in the report.
        """
        bill_data = [{
            'partner_id': partner.id,
            'move_type': 'in_invoice',
            'date': '2017-01-02',
            'invoice_date': '2017-01-02',
            'invoice_line_ids': [
                Command.create({
                    'name': 'Line 1',
                    'product_id': self.product_a.id,
                    'account_id': account.id,
                    'quantity': 1,
                    'price_unit': 1000,
                    'tax_ids': [Command.set(product_taxes.ids)],
                }),
            ]
        } for partner, product_taxes, account in (
            (self.company_data['company'].partner_id, self.company_data['default_tax_purchase'], self.company_data['default_account_expense']),
            (self.company_data_2['company'].partner_id, self.iva_purchase_tax + self.rte_iva_15_over_19_purchase_tax, self.test_account),
            (self.company_data_2['company'].partner_id, self.iva_purchase_tax, self.test_account),
        )]
        self.env['account.move'].create(bill_data).action_post()

        report = self.env['l10n_co_reports.certification_report.iva']
        options = self._init_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))

        self.assertLinesValues(
            report._get_table(options)[1],
            #   Name                 Tax Base Amount   Balance 15 over 19   Balance
            [   0,                   2,                3,                   4],
            [
                ('company_2_data',   1000.0,           190.0,               28.5),
            ],
        )

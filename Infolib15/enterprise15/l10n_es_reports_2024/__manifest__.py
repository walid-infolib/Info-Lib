# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spain - Accounting Reports (2024 Update)",
    'description': """
        Modelo 303: New fields [108] and [111] (HAC/819/2024) and extra fields regarding to Rectificación
    """,
    'category': 'Accounting/Localization',
    'version': '1.0',
    'depends': ['l10n_es_reports'],
    'data': [
        'wizard/aeat_boe_export_wizards.xml',
        'wizard/aeat_tax_reports_wizards.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}

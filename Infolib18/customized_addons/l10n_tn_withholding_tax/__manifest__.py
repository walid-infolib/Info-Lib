{
    'name': "Tunisian: Withholding tax - Retenue à la source",
    'sequence': 2,
    'version': '18.0.0.0.0',
    'depends': ['l10n_tn', 'infolib_base_vat_tn'],
    'author': "Info'Lib",
    'website': "https://www.infolib.tn/",
    'category': 'Accounting/Accounting',
    "license": "OPL-1",
    "price": 24.99,
    'description': """Withholding tax module is preserved to manage the withholding tax logic in relation with 
    purchase, sale and accounting apps. """,

    'data': [
        "security/ir.model.access.csv",
        "data/template/withholding_tax_data.xml",
        "report/ir_actions_report.xml",
        "report/report_withholding_tax_structure.xml",
        "views/account_payment_view.xml",
        "views/withholding_tax_view.xml",
        "wizards/account_payment_register_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'images': ['images/infolib_tn.png']

}

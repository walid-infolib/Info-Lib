{
    'name': "Tunisian: Tax Stamp - Timbre Fiscal",
    'summary': """Tax Stamp on Customer/supplier invoices""",
    'description': """
       This module adds functionality for managing stamp tax in invoices.
    """,
    "license": "OPL-1",
    "price": 4.94,
    'author': "Info'Lib",
    'website': "https://www.infolib.tn/",
    'category': 'Accounting',
    'version': '17.0.0.0.0',
    'depends': [
        'account',
    ],
    'data': [
        'report/report_invoice.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'images': ['images/infolib_tn.png']
}

# -*- coding: utf-8 -*-
{
    'name': "Tunisia: Payroll",
    'summary': "Include Tunisian Payroll",
    'description': """A module to add Tunisian Payroll""",
    'author': "Info'Lib",
    'category': 'Human Resources/Payroll',
    'version': '17.0.0.0.0',
    'depends': ['hr_payroll'],
    'data': [
        'data/collective_agreement_data.xml',
        'security/ir.model.access.csv',
        'views/convention_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_payroll_structure_type_views.xml',
    ],
    'installable': False,
    'license': 'OPL-1',
    'price': 100,
    'images': ['static/description/cover_540_270.png']
}
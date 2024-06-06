# -*- coding: utf-8 -*-
{
    'name': "Tunisia: Declaration CNSS",
    'summary': "Include Tunisian CNSS in the contracts of your employees",
    'description': """A module to add CNSS declaration to the employee's""",
    'author': "Info'Lib",
    'category': 'Human Resources/Employees',
    'version': '17.0.0.0.0',
    'depends': ['hr_payroll'],
    'data': [
        'security/ir.model.access.csv',
        'report/paperformat.xml',
        'report/report_cnss_declaration.xml',
        'data/contract_type_data.xml',
        'views/res_company.xml',
        'views/hr_contract_type_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_cnss.xml',
    ],
    'installable': True,
    'license': 'OPL-1',
    'price': 94.08,
    'images': ['static/description/cover_540_270.png']
}
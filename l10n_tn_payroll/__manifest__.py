# -*- coding: utf-8 -*-
{
    'name': "Tunisia: Payroll",
    'summary': "Include Tunisian Payroll",
    'description': """A module to add Tunisian Payroll""",
    'author': "Info'Lib",
    'category': 'Human Resources/Payroll',
    'version': '17.0.0.0.0',
    'depends': ['cnss_declaration'],
    'data': [
        'data/collective_agreement_data.xml',
        'data/hr_payroll_data_tn.xml',
        'data/hr_work_entry_data.xml',
        'security/ir.model.access.csv',
        'views/report_payslip_templates.xml',
        'views/convention_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_payroll_structure_type_views.xml',
        'views/hr_salary_rule.xml',
    ],
    'installable': True,
    'license': 'OPL-1',
    'price': 500,
    'images': ['static/description/cover_540_270_paie_tunisie.gif']
}
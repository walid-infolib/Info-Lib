from odoo import api, fields, models


class ContractType(models.Model):
    _inherit = 'hr.contract.type'

    exploit_code = fields.Char(string="Exploit code", help="Exploit code", size=4)
    cnss_salary_rate = fields.Float(string="CNSS salary rate", help="CNSS salary rate")
    employer_cnss_rate = fields.Float(string="Employer cnss rate", help="Employer cnss rate")
    tfp = fields.Float(string="TFP", help="The Professional Training Tax")
    foprolos = fields.Float(string="FOPROLOS", help="Social Housing Promotion Fund")
    taxable = fields.Boolean(string="Taxable", help="Taxable", default=True)


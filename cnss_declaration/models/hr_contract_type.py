from odoo import fields, models


class ContractType(models.Model):
    _inherit = "hr.contract.type"

    exploit_code = fields.Char(string="Exploit code", size=4)
    cnss_salary_rate = fields.Float(string="CNSS salary rate")
    employer_cnss_rate = fields.Float(string="Employer CNSS rate")
    work_accident = fields.Float(string="Work accident rate")
    tfp = fields.Float(string="TFP", help="The Professional Training Tax")
    foprolos = fields.Float(string="FOPROLOS", help="Social Housing Promotion Fund")
    taxable = fields.Boolean(string="Taxable", help="Taxable", default=True)

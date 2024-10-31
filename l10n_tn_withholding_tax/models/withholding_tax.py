from odoo import fields, models


class WithholdingTax(models.Model):
    _name = "withholding.tax"
    _description = "Withholding Tax"

    name = fields.Char(string="Name")
    amount = fields.Float(string="Amount")
    designation = fields.Char(string="Designation")
    account_customer_id = fields.Many2one("account.account", string="Customer Account")
    account_supplier_id = fields.Many2one("account.account", string="Supplier Account")

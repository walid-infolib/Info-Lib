# Developed by Info'Lib. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models, fields


class PaymentIcon(models.Model):
    _inherit = 'payment.icon'

    code = fields.Char()

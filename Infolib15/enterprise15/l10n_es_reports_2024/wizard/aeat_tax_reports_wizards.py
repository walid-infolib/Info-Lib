# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Mod303Wizard(models.TransientModel):
    _inherit = 'l10n_es_reports.mod303.wizard'

    casilla_108 = fields.Monetary(
        string="[108] Exclusivamente para determinados supuestos de autoliquidación rectificativa por discrepancia de criterio administrativo que no deban incluirse en otras casillas. Otros ajustes",
    )
    casilla_111 = fields.Monetary(string="[111] Rectificación - Importe")

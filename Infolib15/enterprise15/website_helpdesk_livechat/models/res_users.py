# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Users(models.Model):
    _inherit = ['res.users']

    def _init_messaging(self):
        values = super()._init_messaging()
        if self.env['helpdesk.team'].search([
            ('use_website_helpdesk_livechat', '=', True),
            ('company_id', 'in', self.env.context.get('allowed_company_ids'))
        ], limit=1):
            values['helpdesk_team_available'] = True
        return values

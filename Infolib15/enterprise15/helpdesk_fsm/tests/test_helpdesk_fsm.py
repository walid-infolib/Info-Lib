# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.helpdesk.tests import common


class TestHelpdeskFSM(common.HelpdeskCommon):

    def test_fsm_project(self):
        # Enable field service on the helpdesk team
        self.test_team.use_fsm = True
        # Find the first fsm project
        fsm_project = self.env['project.project'].search([('is_fsm', '=', True), ('company_id', '=', self.test_team.company_id.id)], limit=1)
        # Default fsm_project should be the first fsm project with the oldest id
        self.assertEqual(self.test_team.fsm_project_id, fsm_project,
                         "The default fsm project should be from the same company.")

    def test_fsm_project_multicompany(self):
        extra_company = self.env['res.company'].create({'name': 'Extra Company'})
        fsm_project = self.env['project.project'].search([('is_fsm', '=', True), ('company_id', '=', extra_company.id)], limit=1)
        self.test_team.write({'company_id': extra_company.id})
        self.test_team.use_fsm = True
        self.assertEqual(self.test_team.fsm_project_id, fsm_project,
                         "The default fsm project should be from the same company.")

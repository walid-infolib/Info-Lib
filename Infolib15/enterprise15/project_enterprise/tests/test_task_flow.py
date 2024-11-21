# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.tests import common

from odoo.addons.mail.tests.common import mail_new_test_user


class TestTaskFlow(common.TransactionCase):

    def setUp(self):
        super().setUp()

        self.resource_calendar = self.env['resource.calendar'].create({
            'name': "UTC schedule",
            'tz': 'UTC',
        })

        self.project_user = mail_new_test_user(
            self.env, login='Armande',
            name='Armande Project_user', email='armande.project_user@example.com',
            notification_type='inbox',
            groups='project.group_project_user',
            resource_calendar_id=self.resource_calendar.id,
        )

        self.project_test = self.env['project.project'].create({
            'name': 'Project Test',
        })

    def test_planning_overlap(self):
        task_A = self.env['project.task'].create({
            'name': 'Fsm task 1',
            'user_ids': self.project_user,
            'project_id': self.project_test.id,
            'planned_date_begin': datetime.now(),
            'planned_date_end': datetime.now() + relativedelta(hours=4)
        })
        task_B = self.env['project.task'].create({
            'name': 'Fsm task 2',
            'user_ids': self.project_user,
            'project_id': self.project_test.id,
            'planned_date_begin': datetime.now() + relativedelta(hours=2),
            'planned_date_end': datetime.now() + relativedelta(hours=6)
        })
        task_C = self.env['project.task'].create({
            'name': 'Fsm task 2',
            'user_ids': self.project_user,
            'project_id': self.project_test.id,
            'planned_date_begin': datetime.now() + relativedelta(hours=5),
            'planned_date_end': datetime.now() + relativedelta(hours=7)
        })
        task_D = self.env['project.task'].create({
            'name': 'Fsm task 2',
            'user_ids': self.project_user,
            'project_id': self.project_test.id,
            'planned_date_begin': datetime.now() + relativedelta(hours=8),
            'planned_date_end': datetime.now() + relativedelta(hours=9)
        })
        self.assertEqual(task_A.planning_overlap, 1, "One task should be overlapping with task_A")
        self.assertEqual(task_B.planning_overlap, 2, "Two tasks should be overlapping with task_B")
        self.assertFalse(task_D.planning_overlap, "No task should be overlapping with task_D")

    def test_default_planned_dates(self):
        """
        Check whether planned dates written to a task get adjusted to working
        hours iff they correspond to a full day.
        This allows tasks planned via Gantt or in batch to have more meaningful
        values, while user-selected dates remaing unaffected.
        """
        task_A, task_B = self.env['project.task'].create([{
            'name': "Regular task",
            'user_ids': self.project_user.ids,
            'project_id': self.project_test.id,
        }, {
            'name': "Overtime task",
            'user_ids': self.project_user.ids,
            'project_id': self.project_test.id,
        }])

        task_A.write({
            'planned_date_begin': '2024-08-08 00:00:00',
            'planned_date_end': '2024-08-08 23:59:59',
        })
        task_B.write({
            'planned_date_begin': '2024-08-08 16:00:00',
            'planned_date_end': '2024-08-08 21:00:00',
        })

        self.assertEqual(task_A.planned_date_begin.hour, 8, "Default start hour should change")
        self.assertEqual(task_A.planned_date_end.hour, 17, "Default end hour should change")
        self.assertEqual(task_B.planned_date_begin.hour, 16, "Custom start shouldn't change")
        self.assertEqual(task_B.planned_date_end.hour, 21, "Custom end shouldn't change")

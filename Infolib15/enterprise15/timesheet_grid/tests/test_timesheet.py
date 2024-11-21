# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import fields, Command
from odoo.osv import expression

from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet
from odoo.exceptions import AccessError

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch


@freeze_time(datetime(2021, 4, 1) + timedelta(hours=12, minutes=21))
class TestTimesheetValidation(TestCommonTimesheet):

    def setUp(self):
        super(TestTimesheetValidation, self).setUp()
        today = fields.Date.today()
        self.timesheet1 = self.env['account.analytic.line'].with_user(self.user_employee).create({
            'name': "my timesheet 1",
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'date': today,
            'unit_amount': 2.0,
        })
        self.timesheet2 = self.env['account.analytic.line'].with_user(self.user_employee).create({
            'name': "my timesheet 2",
            'project_id': self.project_customer.id,
            'task_id': self.task2.id,
            'date': today,
            'unit_amount': 3.11,
        })

    def test_timesheet_validation_user(self):
        """ Employee record its timesheets and Officer validate them. Then try to modify/delete it and get Access Error """
        # Officer validate timesheet of 'user_employee' through wizard
        timesheet_to_validate = self.timesheet1 | self.timesheet2
        timesheet_to_validate.with_user(self.user_manager).action_validate_timesheet()

        # Check timesheets 1 and 2 are validated
        self.assertTrue(self.timesheet1.validated)
        self.assertTrue(self.timesheet2.validated)

        # Employee can not modify validated timesheet
        with self.assertRaises(AccessError):
            self.timesheet1.with_user(self.user_employee).write({'unit_amount': 5})
        # Employee can not delete validated timesheet
        with self.assertRaises(AccessError):
            self.timesheet2.with_user(self.user_employee).unlink()

        # Employee can still create new timesheet before the validated date
        last_month = datetime.now() - relativedelta(months=1)
        self.env['account.analytic.line'].with_user(self.user_employee).create({
            'name': "my timesheet 3",
            'project_id': self.project_customer.id,
            'task_id': self.task2.id,
            'date': last_month,
            'unit_amount': 2.5,
        })

        # Employee can still create timesheet after validated date
        next_month = datetime.now() + relativedelta(months=1)
        timesheet4 = self.env['account.analytic.line'].with_user(self.user_employee).create({
            'name': "my timesheet 4",
            'project_id': self.project_customer.id,
            'task_id': self.task2.id,
            'date': next_month,
            'unit_amount': 2.5,
        })
        # And can still update non validated timesheet
        timesheet4.write({'unit_amount': 7})

    def test_timesheet_validation_manager(self):
        """ Officer can see timesheets and modify the ones of other employees """
       # Officer validate timesheet of 'user_employee' through wizard
        timesheet_to_validate = self.timesheet1 | self.timesheet2
        timesheet_to_validate.with_user(self.user_manager).action_validate_timesheet()
        # manager modify validated timesheet
        self.timesheet1.with_user(self.user_manager).write({'unit_amount': 5})

    def test_timesheet_validation_stop_timer(self):
        """ Check that the timers are stopped when validating the task even if the timer belongs to another user """
        # Start timer with employee user
        timesheet = self.timesheet1
        start_unit_amount = timesheet.unit_amount
        timesheet.with_user(self.user_employee).action_timer_start()
        timer = self.env['timer.timer'].search([("user_id", "=", self.user_employee.id), ('res_model', '=', 'account.analytic.line')])
        self.assertTrue(timer, 'A timer has to be running for the user employee')
        # Validate timesheet with manager user
        timesheet.with_user(self.user_manager).action_validate_timesheet()
        # Check if old timer is stopped
        self.assertFalse(timer.exists())
        # Check if time spent is add to the validated timesheet
        self.assertGreater(timesheet.unit_amount, start_unit_amount, 'The unit amount has to be greater than at the beginning')

    def _test_next_date(self, now, result, delay, interval):

        def _now(*args, **kwargs):
            return now

        # To allow testing

        patchers = [patch('odoo.fields.Datetime.now', _now)]

        for p in patchers:
            p.start()

        self.user_manager.company_id.write({
            'timesheet_mail_manager_interval': interval,
            'timesheet_mail_manager_delay': delay,
        })

        self.assertEqual(result, self.user_manager.company_id.timesheet_mail_manager_nextdate)

        for p in patchers:
            p.stop()

    def test_timesheet_next_date_reminder_neg_delay(self):

        result = datetime(2020, 4, 23, 8, 8, 15)
        now = datetime(2020, 4, 22, 8, 8, 15)
        self._test_next_date(now, result, -3, "weeks")

        result = datetime(2020, 4, 30, 8, 8, 15)
        now = datetime(2020, 4, 23, 8, 8, 15)
        self._test_next_date(now, result, -3, "weeks")
        now = datetime(2020, 4, 24, 8, 8, 15)
        self._test_next_date(now, result, -3, "weeks")
        now = datetime(2020, 4, 25, 8, 8, 15)
        self._test_next_date(now, result, -3, "weeks")

        result = datetime(2020, 4, 27, 8, 8, 15)
        now = datetime(2020, 4, 26, 8, 8, 15)
        self._test_next_date(now, result, -3, "months")

        result = datetime(2020, 5, 28, 8, 8, 15)
        now = datetime(2020, 4, 27, 8, 8, 15)
        self._test_next_date(now, result, -3, "months")
        now = datetime(2020, 4, 28, 8, 8, 15)
        self._test_next_date(now, result, -3, "months")
        now = datetime(2020, 4, 29, 8, 8, 15)
        self._test_next_date(now, result, -3, "months")

        result = datetime(2020, 2, 27, 8, 8, 15)
        now = datetime(2020, 2, 26, 8, 8, 15)
        self._test_next_date(now, result, -3, "weeks")

        result = datetime(2020, 3, 5, 8, 8, 15)
        now = datetime(2020, 2, 27, 8, 8, 15)
        self._test_next_date(now, result, -3, "weeks")
        now = datetime(2020, 2, 28, 8, 8, 15)
        self._test_next_date(now, result, -3, "weeks")
        now = datetime(2020, 2, 29, 8, 8, 15)
        self._test_next_date(now, result, -3, "weeks")

        result = datetime(2020, 2, 26, 8, 8, 15)
        now = datetime(2020, 2, 25, 8, 8, 15)
        self._test_next_date(now, result, -3, "months")

        result = datetime(2020, 3, 28, 8, 8, 15)
        now = datetime(2020, 2, 26, 8, 8, 15)
        self._test_next_date(now, result, -3, "months")
        now = datetime(2020, 2, 27, 8, 8, 15)
        self._test_next_date(now, result, -3, "months")
        now = datetime(2020, 2, 28, 8, 8, 15)
        self._test_next_date(now, result, -3, "months")

    def test_minutes_computing_after_timer_stop(self):
        """ Test if unit_amount is updated after stoping a timer """
        Timesheet = self.env['account.analytic.line']
        timesheet_1 = Timesheet.with_user(self.user_employee).create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': '/',
            'unit_amount': 1,
        })

        # When the timer is greater than 1 minute
        now = datetime.now()
        timesheet_1.with_user(self.user_employee).action_timer_start()
        timesheet_1.with_user(self.user_employee).user_timer_id.timer_start = now - timedelta(minutes=1, seconds=28)
        timesheet_1.with_user(self.user_employee).action_timer_stop()

        self.assertGreater(timesheet_1.unit_amount, 1, 'unit_amount should be greated than his last value')

    def test_timesheet_display_timer(self):
        current_timesheet_uom = self.env.company.timesheet_encode_uom_id

        # self.project_customer.allow_timesheets = True

        self.env.company.timesheet_encode_uom_id = self.env.ref('uom.product_uom_hour')
        self.assertTrue(self.timesheet1.display_timer)

        # Force recompute field
        self.env.company.timesheet_encode_uom_id = self.env.ref('uom.product_uom_day')
        self.timesheet1._compute_display_timer()
        self.assertFalse(self.timesheet1.display_timer)

        self.env.company.timesheet_encode_uom_id = current_timesheet_uom

    def test_add_time_from_wizard(self):
        wizard = self.env['project.task.create.timesheet'].create({
            'time_spent': 0.15,
            'task_id': self.task1.id,
        })
        wizard.with_user(self.env.user).save_timesheet()
        self.assertEqual(self.task1.timesheet_ids[0].unit_amount, 0.15)

    def test_action_add_time_to_timer_multi_company(self):
        company = self.env['res.company'].create({'name': 'My_Company'})
        self.env['hr.employee'].with_company(company).create({
            'name': 'coucou',
            'user_id': self.user_manager.id,
        })
        self.user_manager.write({'company_ids': [Command.link(company.id)]})
        timesheet = self.env['account.analytic.line'].with_user(self.user_manager).create({'name': 'coucou', 'project_id': self.project_customer.id})
        timesheet.with_user(self.user_manager).action_add_time_to_timer(1)

    def test_working_hours_for_employees(self):
        """Trying to access working hours for employees that might
           include employees from another company than the allowed
           ones should not raise a multi company access error and
           return working hours for employees of allowed companies."""
        Employee = self.env['hr.employee']
        company = self.env['res.company'].create({'name': 'My_Company'})
        self.user_manager.write({'company_ids': [Command.link(company.id)]})
        empl_manager_2 = Employee.with_company(company).create({
            'name': 'Juste Leblanc',
            'user_id': self.user_manager.id,
        })
        employees_grid_data = [{
            'employee_id': self.empl_manager.id,
            'employee_display_name': self.empl_manager.name,
            'grid_row_index': 0
        }]

        Employee = Employee.with_user(self.user_manager).with_context(allowed_company_ids=[company.id])

        # Should not raise a multi company access error and return no working hours
        working_hours = Employee.get_timesheet_and_working_hours_for_employees(employees_grid_data, '2021-12-01', '2021-12-31')
        self.assertEqual(len(working_hours), 0, "Should have found no working hours")

        employees_grid_data.append({
            'employee_id': empl_manager_2.id,
            'employee_display_name': empl_manager_2.name,
            'grid_row_index': 1
        })

        # Should not raise a multi company access error and return working hours for employees of allowed companies
        working_hours = Employee.get_timesheet_and_working_hours_for_employees(employees_grid_data, '2021-12-01', '2021-12-31')
        self.assertEqual(len(working_hours), 1, "Should have working hours only for employee of allowed companies (empl_manager_2)")
        self.assertEqual(working_hours[empl_manager_2.id]['units_to_work'], 184.0, "Number of hours should be 23d * 8h/d = 184h")

    def test_timesheet_grid_filter_equal_string(self):
        """Make sure that if you use a filter with (not) equal to,
           there won't be any error with grid view"""
        row_fields = ['project_id', 'task_id']
        col_field = 'date'
        cell_field = 'unit_amount'
        domain = [['employee_id', '=', self.user_employee.employee_id.id],
                  ['project_id', '!=', False]]
        range = {'name': 'week', 'string': 'Week', 'span': 'week', 'step': 'day'}
        orderby = 'project_id,task_id'

        # Filter on project equal a different name, expect 0 row
        new_domain = expression.AND([domain, [('project_id', '=', self.project_customer.name[:-1])]])
        result = self.env['account.analytic.line'].read_grid(row_fields, col_field, cell_field, domain=new_domain, range=range, orderby=orderby)
        self.assertFalse(result['rows'])

        # Filter on project not equal to exact name, expect 0 row
        new_domain = expression.AND([domain, [('project_id', '!=', self.project_customer.name)]])
        result = self.env['account.analytic.line'].read_grid(row_fields, col_field, cell_field, domain=new_domain, range=range, orderby=orderby)
        self.assertFalse(result['rows'])

        # Filter on project_id to make sure there are timesheets
        new_domain = expression.AND([domain, [('project_id', '=', self.project_customer.name)]])
        result = self.env['account.analytic.line'].read_grid(row_fields, col_field, cell_field, domain=new_domain, range=range, orderby=orderby)
        self.assertEqual(len(result['rows']), 2)

        # Filter on task equal to task1, expect timesheet1 (task 1)
        new_domain = expression.AND([domain, [('task_id', '=', self.timesheet1.task_id.name)]])
        result = self.env['account.analytic.line'].read_grid(row_fields, col_field, cell_field, domain=new_domain, range=range, orderby=orderby)
        self.assertEqual(len(result['rows']), 1)
        self.assertEqual(result['rows'][0]['values']['project_id'][0], self.timesheet1.project_id.id)
        self.assertEqual(result['rows'][0]['values']['task_id'][0], self.timesheet1.task_id.id)

        # Filter on task not equal to task1, expect timesheet2 (task 2)
        new_domain = expression.AND([domain, [('task_id', '!=', self.timesheet1.task_id.name)]])
        result = self.env['account.analytic.line'].read_grid(row_fields, col_field, cell_field, domain=new_domain, range=range, orderby=orderby)
        self.assertEqual(len(result['rows']), 1)
        self.assertEqual(result['rows'][0]['values']['project_id'][0], self.timesheet2.project_id.id)
        self.assertEqual(result['rows'][0]['values']['task_id'][0], self.timesheet2.task_id.id)

    def test_adjust_grid(self):
        today_date = fields.Date.today()
        company = self.env['res.company'].create({'name': 'My_Company'})
        employee = self.env['hr.employee'].with_company(company).create({
            'name': 'coucou',
            'timesheet_manager_id': self.user_manager.id,
        })

        Timesheet = self.env['account.analytic.line']
        timesheet = Timesheet.with_user(self.user_manager).create({
            'employee_id': employee.id,
            'project_id': self.project_customer.id,
            'date': today_date,
            'unit_amount': 2,
        })
        timesheet.with_user(self.user_manager).action_validate_timesheet()

        column_date = f'{today_date}/{today_date + timedelta(days=1)}'
        Timesheet.adjust_grid([('id', '=', timesheet.id)], 'date', column_date, 'unit_amount', 3.0)

        self.assertEqual(Timesheet.search_count([('employee_id', '=', employee.id)]), 2, "Should create new timesheet instead of updating validated timesheet in cell")

    def test_get_last_week(self):
        """Test the get_last_week method. It should return grid_anchor (GA), last_week (LW),
            where last_week is first Sunday before GA - 7 days. Example:
            Su Mo Tu We Th Fr Sa
            LW -- -- -- -- -- --
            -- -- GA -- -- -- --
        """
        AnalyticLine = self.env['account.analytic.line']
        for d in range(8, 22):
            grid_anchor = datetime(2023, 1, d)
            dummy, last_week = AnalyticLine.with_context(grid_anchor=grid_anchor)._get_last_week()
            self.assertEqual(last_week, date(2023, 1, ((d - 1) // 7 - 1) * 7 + 1))

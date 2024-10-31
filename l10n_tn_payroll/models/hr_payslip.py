from odoo import models


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    def _get_worked_day_lines(self, domain=None, check_out_of_contract=True):
        res = super()._get_worked_day_lines(
            domain=domain, check_out_of_contract=check_out_of_contract
        )
        ############################################################
        # Force the number of presence according to the configuration made on the type of structure.
        # This is only valid in the case of Default Wage Type is monthly
        ############################################################
        if (
            self.struct_id.type_id.wage_type == "monthly"
            and self.struct_id.type_id.default_work_entry_days
        ):
            default_work_entry_days = self.struct_id.type_id.default_work_entry_days
            default_work_entry_hours = self.struct_id.type_id.default_work_entry_hours
            for worked in res:
                work_entry_type_id = self.env["hr.work.entry.type"].browse(
                    worked["work_entry_type_id"]
                )
                if (
                    work_entry_type_id
                    != self.struct_id.type_id.default_work_entry_type_id
                    and work_entry_type_id.is_leave
                ):
                    default_work_entry_days -= worked["number_of_days"]
                    default_work_entry_hours -= worked["number_of_hours"]
                elif (
                    work_entry_type_id
                    == self.struct_id.type_id.default_work_entry_type_id
                ):
                    worked["number_of_days"] = default_work_entry_days
                    worked["number_of_hours"] = default_work_entry_hours
        return res

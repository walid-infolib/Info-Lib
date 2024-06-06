import base64
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

from odoo17.odoo.tools import date_utils


class HrCnss(models.Model):
    _name = "hr.cnss"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date desc"
    _description = ("The National Social Security Fund (CNSS) allows you to check "
                    "the quarterly declaration of employees and wages")

    name = fields.Char(string="Title", compute="_compute_name", store=True)
    quarter = fields.Selection([('1', '1'), ('4', '2'), ('7', '3'), ('10', '4')], string='Quarter',
                               help="Choose the quarter of the quarterly declaration of employees and wages")
    year = fields.Selection(selection='year_selection', string="Year", default=datetime.now().strftime('%Y'),
                            help="Choose the year of the quarterly declaration of employees and wages  ")
    contract_type_id = fields.Many2one('hr.contract.type', "Contract Type")
    start_date = fields.Date(compute='_compute_quarter_year_date', string="start date", store=True)
    end_date = fields.Date(compute='_compute_quarter_year_date', string="end date", store=True)
    date = fields.Date(string="Date Of Declaration", help="Date Of Declaration",
                       default=datetime.today())
    line_ids = fields.One2many('hr.cnss.line', 'cnss_id')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', 'Currency', compute='_compute_currency_id', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')],
        string='Status', readonly=True, copy=False,
        default='draft', tracking=True,
        help="""* When the Cnss declaration is created the status is \'Draft\'.
                    \n* If the Cnss declaration is confirmed then status is set to \'Done\'.""")
    total_sum = fields.Monetary(string='Total sum', compute='_compute_total_sum', store=True)

    def generate_info_file(self):
        employee_ids = []
        if not self.company_id.ssnid:
            raise UserError(_("SSN N° Company is empty"))
        num_employer = self.company_id.ssnid.zfill(10)
        if not self.contract_type_id.exploit_code:
            raise UserError(_("Exploit Code in the contrat type is empty"))
        exploit_code = self.contract_type_id.exploit_code.zfill(4)
        quarter = dict(self._fields['quarter'].selection).get(self.quarter)
        year = self.year
        for line in self.line_ids:
            page = str(line.page).zfill(3)
            line_num = str(line.line).zfill(2)
            employee = "{:60}".format(line.employee_id.name.upper())
            if line.ssnid:
                ssnid = line.ssnid.zfill(10)
            else:
                ssnid = ''.zfill(10)
            if line.employee_id.identification_id:
                identification_id = line.employee_id.identification_id.zfill(8)
            else:
                raise UserError(_("Employee %s not have a identification number!") % line.employee_id.name)
            salary = str(line.total).replace(".", "").zfill(10)
            blank_area = ''.zfill(10)
            employee_ids.append(f"{num_employer}{exploit_code}{quarter}{year}{page}{line_num}"
                                f"{ssnid}{employee}{identification_id}{salary}{blank_area}")

        info_content = "\n".join(str(x) for x in employee_ids)
        doc_name = "DS" + num_employer + exploit_code + '.' + quarter + year
        self.env['ir.attachment'].search([('name', '=', doc_name),
                                          ('res_id', '=', self.id),
                                          ('res_model', '=', 'hr.cnss')]).unlink()
        attachment_values = {
            'name': doc_name,
            'type': 'binary',
            'datas': base64.b64encode(info_content.encode('utf-8')),
            'mimetype': 'text/plain',
            'res_id': self.id,
            'res_model': 'hr.cnss'
        }
        self.env['ir.attachment'].create(attachment_values)
        self.write({'state': 'done'})

    @api.ondelete(at_uninstall=False)
    def _unlink_cnss(self):
        for record in self:
            if record.state == 'done':
                raise ValidationError("You can not delete a confirmed CNSS declaration."
                                      " You must first cancel it.")

    @api.depends('line_ids.total')
    def _compute_total_sum(self):
        for record in self:
            record.total_sum = sum(line.total for line in record.line_ids)

    @api.depends("quarter", "year")
    def _compute_name(self):
        for record in self:
            name_cnss = dict(record._fields['quarter'].selection).get(record.quarter)
            if name_cnss:
                record.name = name_cnss + "-" + record.year
            else:
                record.name = ""

    def action_print_declaration_cnss(self):
        return self.env.ref('cnss_declaration.report_cnss_declaration_template').report_action(self)

    def action_draft(self):
        if self.state == 'done':
            # Delete attachments if they exist
            attachments = self.env['ir.attachment'].search([
                ('res_id', '=', self.id),
                ('res_model', '=', 'hr.cnss')
            ])
            attachments.unlink()
        self.write({'state': 'draft'})

    @api.constrains('quarter', 'year', 'contract_type_id')
    def _check_cnss_declaration(self):
        for i in self:
            declarations = self.env['hr.cnss'].search_count(
                [('quarter', '=', i.quarter),
                 ('year', '=', i.year),
                 ('contract_type_id', '=', i.contract_type_id.id),
                 ('company_id', '=', i.company_id.id)])
            if declarations > 1:
                raise ValidationError(_("You already have a declaration on this date of the quarter with this year"))

    @api.depends('company_id')
    def _compute_currency_id(self):
        for order in self:
            order.currency_id = order.company_id.currency_id

    @api.depends('quarter', 'year')
    def _compute_quarter_year_date(self):
        for record in self:
            if record.quarter and record.year:
                dte = datetime.strptime('01/' + record.quarter + '/' + record.year, '%d/%m/%Y')
                dte_start, dte_end = date_utils.get_quarter(dte)
                record.start_date = dte_start
                record.end_date = dte_end
            else:
                record.start_date = False
                record.end_date = False

    @api.model
    def year_selection(self):
        now = datetime.now()
        year = int(now.strftime('%Y')) - 10
        end_year = int(now.strftime('%Y'))

        year_list = []
        while year <= end_year:
            year_list.append((str(year), str(year)))
            year += 1
        return list(reversed(year_list))

    @api.onchange('quarter', 'year', 'contract_type_id')
    def _get_lines(self):
        if self.quarter and self.year and self.contract_type_id:
            self.line_ids = False
            date_month_start = datetime.strptime(str(self.start_date), "%Y-%m-%d").strftime('%b')[0]
            date_month_end = datetime.strptime(str(self.end_date), "%Y-%m-%d").strftime('%b')[0]
            payslip_data = self.env['hr.payslip'].read_group(domain=[('date_from', '>=', self.start_date),
                                                                     ('date_to', '<=', self.end_date),
                                                                     ('state', 'in', ['done', 'paid']),
                                                                     ('contract_id.contract_type_id',
                                                                      '=', self.contract_type_id.id)
                                                                     ],
                                                             fields=['employee_id', 'date_from', 'gross_wage'],
                                                             groupby=['employee_id', 'date_from:month'],
                                                             lazy=False)
            employee_data = {}
            for i in payslip_data:
                employee_id = i['employee_id'][0]
                month = i['date_from:month'][0]
                if month is not None:
                    gross_wage = i['gross_wage']
                    if employee_id not in employee_data:
                        employee_data[employee_id] = {'gross_1': 0, 'gross_2': 0, 'gross_3': 0}
                    if month == date_month_start:
                        employee_data[employee_id]['gross_1'] += gross_wage
                    elif month == date_month_end:
                        employee_data[employee_id]['gross_3'] += gross_wage
                    else:
                        employee_data[employee_id]['gross_2'] += gross_wage
            page = 1
            line_num = 1
            for employee_id, data in employee_data.items():
                total = data['gross_1'] + data['gross_2'] + data['gross_3']
                self.line_ids = [(0, 0, {'page': page, 'line': line_num,
                                         'employee_id': employee_id,
                                         'gross_1': data['gross_1'],
                                         'gross_2': data['gross_2'],
                                         'gross_3': data['gross_3'],
                                         'total': total})]
                if line_num == 12:
                    line_num = 1
                    page += 1
                else:
                    line_num += 1

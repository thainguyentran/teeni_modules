# -*- coding: utf-8 -*-
import math
import time

from datetime import datetime, timedelta, date
import calendar
from dateutil import rrule, parser
from dateutil.relativedelta import relativedelta
import odoo.tools as tools
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError, Warning
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF, \
    DEFAULT_SERVER_DATETIME_FORMAT as DSDTF

import pytz

import base64

import logging

_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @api.onchange('employee_id', 'date_from', 'date_to')
    def onchange_employee(self):

        if self.worked_days_line_ids:
            self.worked_days_line_ids = [(6, 0, [])]

        if self.employee_id and self.employee_id.id:
            employee_id = self.employee_id and self.employee_id.id
        else:
            employee_id = self._context.get('employee_id', False)

        if self.date_from:
            date_from = self.date_from
        else:
            date_from = self._context.get('date_from', False)

        if self.date_to:
            date_to = self.date_to
        else:
            date_to = self._context.get('date_to', False)

        if self.contract_id and self.contract_id.id:
            contract_id = self.contract_id and self.contract_id.id
        else:
            contract_id = self._context.get('contract_id', False)

        if (not employee_id) or (not date_from) or (not date_to):
            return {}

        empolyee_obj = self.env['hr.employee']
        period_start_date = date_from
        period_end_date = date_to
        s_contract_id = []
        # delete old worked days lines
        old_worked_days_ids = []
        if self.id:
            old_worked_days_ids = [worked_days_rec.id for worked_days_rec in
                                   self.env['hr.payslip.worked_days'].search([
                                       ('payslip_id', '=', self.id)])]
        if old_worked_days_ids:
            self._cr.execute(""" delete from hr_payslip_worked_days \
                                where id in %s""", (tuple(old_worked_days_ids),))
        # delete old input lines
        old_input_ids = []
        if self.id:
            old_input_ids = [input_rec.id for input_rec in
                             self.env['hr.payslip.input'].search([
                                 ('payslip_id', '=', self.id)])]
        if old_input_ids:
            self._cr.execute(""" delete from hr_payslip_input where \
                                    id in %s""", (tuple(old_input_ids),))
        res = {'value': {
            'line_ids': [],
            'input_line_ids': [],
            'worked_days_line_ids': [],
            # 'details_by_salary_head':[], TODO put me back
            'name': '',
            'contract_id': False,
            'struct_id': False,
        }
        }
        ttyme = datetime.fromtimestamp(time.mktime(time.strptime(
            str(date_from),
            "%Y-%m-%d")))
        employee_brw = empolyee_obj.browse(employee_id)
        res['value'].update({
            'name': _('Salary Slip of %s for %s') % (
                employee_brw.name, tools.ustr(ttyme.strftime('%B-%Y'))
            ),
            'company_id': employee_brw.company_id and
                          employee_brw.company_id.id or False
        })
        if not self._context.get('contract', False):
            # fill with the first contract of the employee
            contract_ids = self.get_contract(employee_brw, date_from, date_to)
            s_contract_id = contract_ids
        else:
            if contract_id:
                # set the list of contract for which the input have to be
                # filled
                contract_ids = [contract_id]
                s_contract_id = contract_ids
            else:
                # if we don't give the contract, then the input to fill should
                # be for all current contracts of the employee
                contract_ids = self.get_contract(employee_brw, date_from,
                                                 date_to)
                s_contract_id = contract_ids
        if not contract_ids:
            return res
        contract_record = self.env['hr.contract'].browse(contract_ids[0])
        res['value'].update({'contract_id': contract_record and
                                            contract_record.id or False})
        struct_record = contract_record and contract_record.struct_id or False
        if not struct_record:
            return res
        res['value'].update({
            'struct_id': struct_record.id,
        })
        # computation of the salary input
        brw_contract_ids = self.env['hr.contract'].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(brw_contract_ids,
                                                         date_from.strftime(
                                                             DSDF),
                                                         date_to.strftime(DSDF
                                                                          ))
        contract_records = self.env['hr.contract'].browse(contract_ids)
        input_line_ids = self.get_inputs(contract_records, date_from, date_to)
        #change in Code
        for rec in input_line_ids:
            if rec['code'] == 'MPAI':
                rec['amount'] = contract_record.mobile_allowance
            if rec['code'] == 'SC123I':
                rec['amount'] = contract_record.housing_allowance
        print("IPLI", input_line_ids)
        #######
        res['value'].update({
            'worked_days_line_ids': worked_days_line_ids,
            'input_line_ids': input_line_ids,
        })
        if not employee_id:
            return res
        active_employee = empolyee_obj.browse(employee_id).active
        res['value'].update({'active_employee': active_employee})
        res['value'].update({'employee_id': employee_id,
                             'date_from': date_from, 'date_to': date_to})
        if date_from and date_to:
            current_date_from = date_from
            current_date_to = date_to
            date_from_cur = date_from
            previous_month_obj = parser.parse(date_from_cur.strftime(DSDF)) - \
                                 relativedelta(months=1)
            total_days = calendar.monthrange(previous_month_obj.year,
                                             previous_month_obj.month)[1]
            first_day_of_previous_month = datetime.strptime("1-" + str(
                previous_month_obj.month) + "-" +
                                                            str(previous_month_obj.year), '%d-%m-%Y')
            last_day_of_previous_month = datetime.strptime(
                str(total_days) + "-" + str(previous_month_obj.month)
                + "-" + str(previous_month_obj.year), '%d-%m-%Y')
            date_from = datetime.strftime(first_day_of_previous_month, DSDF)
            date_to = datetime.strftime(last_day_of_previous_month, DSDF)
            dates = list(rrule.rrule(rrule.DAILY,
                                     dtstart=parser.parse(date_from),
                                     until=parser.parse(date_to)))
            sunday = saturday = weekdays = 0
            for day in dates:
                if day.weekday() == 5:
                    saturday += 1
                elif day.weekday() == 6:
                    sunday += 1
                else:
                    weekdays += 1
            new = {'code': 'TTLPREVDAYINMTH', 'name': 'Total number of days for \
                        previous month', 'number_of_days': len(dates),
                   'sequence': 2, 'contract_id': contract_record.id}
            res.get('value').get('worked_days_line_ids').append(new)
            new = {'code': 'TTLPREVSUNINMONTH', 'name': 'Total sundays in \
                        previous month', 'number_of_days': sunday,
                   'sequence': 3, 'contract_id': contract_record.id}
            res.get('value').get('worked_days_line_ids').append(new)
            new = {'code': 'TTLPREVSATINMONTH', 'name': 'Total saturdays in \
                        previous month', 'number_of_days': saturday,
                   'sequence': 4, 'contract_id': contract_record.id}
            res.get('value').get('worked_days_line_ids').append(new)
            new = {'code': 'TTLPREVWKDAYINMTH', 'name': 'Total weekdays in \
                        previous month', 'number_of_days': weekdays,
                   'sequence': 5, 'contract_id': contract_record.id}
            res.get('value').get('worked_days_line_ids').append(new)

            #             =============added no holidays in current month==========
            f = period_end_date
            count = 0
            currentz_yearz = datetime.strptime(str(f), DSDF).year
            currentz_mnthz = datetime.strptime(str(f), DSDF).month

            holiday_brw = self.env['hr.holiday.public'].search([
                ('state', '=',
                 'validated')])
            if holiday_brw and holiday_brw.ids:
                for line in holiday_brw:
                    if line.holiday_line_ids and line.holiday_line_ids.ids:
                        for holiday in line.holiday_line_ids:
                            holidyz_mnth = datetime.strptime(
                                str(holiday.holiday_date), DSDF
                            ).month
                            holiday_year = datetime.strptime(
                                str(holiday.holiday_date), DSDF
                            ).year
                            if currentz_yearz == holiday_year and \
                                holidyz_mnth == currentz_mnthz:
                                count = count + 1

            new = {'code': 'PUBLICHOLIDAYS', 'name': 'Total Public Holidays in\
                        current month', 'number_of_days': count,
                   'sequence': 6, 'contract_id': contract_record.id}
            res.get('value').get('worked_days_line_ids').append(new)

            #             ===============end of holiday calculation===========
            this_month_obj = parser.parse(date_from_cur.strftime(DSDF)
                                          ) + relativedelta(months=1, days=-1)
            dates = list(rrule.rrule(rrule.DAILY,
                                     dtstart=parser.parse(str(current_date_from
                                                              )),
                                     until=parser.parse(str(current_date_to))))
            total_days_cur_month = calendar.monthrange(this_month_obj.year,
                                                       this_month_obj.month)[1]
            first_day_of_current_month = datetime.strptime(
                "1-" + str(this_month_obj.month) + "-" + str(
                    this_month_obj.year), '%d-%m-%Y')
            last_day_of_current_month = datetime.strptime(
                str(total_days_cur_month) +
                "-" + str(this_month_obj.month) +
                "-" + str(this_month_obj.year),
                '%d-%m-%Y')
            th_current_date_from = datetime.strftime(
                first_day_of_current_month, DSDF)
            th_current_date_to = datetime.strftime(last_day_of_current_month,
                                                   DSDF)
            cur_dates = list(rrule.rrule(rrule.DAILY,
                                         dtstart=parser.parse(
                                             th_current_date_from),
                                         until=parser.parse(th_current_date_to)))
            sunday = saturday = weekdays = 0
            cur_sunday = cur_saturday = cur_weekdays = 0
            for day in dates:
                if day.weekday() == 5:
                    saturday += 1
                elif day.weekday() == 6:
                    sunday += 1
                else:
                    weekdays += 1
            for day in cur_dates:
                if day.weekday() == 5:
                    cur_saturday += 1
                elif day.weekday() == 6:
                    cur_sunday += 1
                else:
                    cur_weekdays += 1
            new = {'code': 'TTLDAYINMTH', 'name': 'Total days for current\
                month', 'number_of_days': len(cur_dates), 'sequence': 7,
                   'contract_id': contract_record.id}
            res.get('value').get('worked_days_line_ids').append(new)
            new = {'code': 'TTLCURRDAYINMTH', 'name': 'Total number of days for \
                        current month', 'number_of_days': len(dates),
                   'sequence': 2, 'contract_id': contract_record.id}
            res.get('value').get('worked_days_line_ids').append(new)
            new = {'code': 'TTLCURRSUNINMONTH', 'name': 'Total sundays in current\
                         month', 'number_of_days': sunday, 'sequence': 3,
                   'contract_id': contract_record.id}
            res.get('value').get('worked_days_line_ids').append(new)
            new = {'code': 'TTLCURRSATINMONTH', 'name': 'Total saturdays in \
                        current month', 'number_of_days': saturday,
                   'sequence': 4, 'contract_id': contract_record.id}
            res.get('value').get('worked_days_line_ids').append(new)
            new = {'code': 'TTLCURRWKDAYINMTH', 'name': 'Total weekdays in \
                        current month', 'number_of_days': weekdays,
                   'sequence': 5, 'contract_id': contract_record.id}
            res.get('value').get('worked_days_line_ids').append(new)
            new = {'code': 'TTLCURRWKDAYINHMTH', 'name': 'Total weekdays in\
                whole current month', 'number_of_days': cur_weekdays,
                   'sequence': 8, 'contract_id': contract_record.id}
            res.get('value').get('worked_days_line_ids').append(new)
            cur_month_weekdays = 0

            if contract_record:
                contract_start_date = contract_record.date_start
                contract_end_date = contract_record.date_end
                if contract_start_date and contract_end_date:

                    if current_date_from <= contract_start_date and \
                        contract_end_date <= current_date_to:
                        current_month_days = list(rrule.rrule(
                            rrule.DAILY, dtstart=parser.parse(str(
                                contract_start_date)),
                            until=parser.parse(str(contract_end_date))))
                        for day in current_month_days:
                            if day.weekday() not in [5, 6]:
                                cur_month_weekdays += 1

                    elif current_date_from <= contract_start_date and \
                        current_date_to <= contract_end_date:
                        current_month_days = list(rrule.rrule(
                            rrule.DAILY, dtstart=parser.parse(str(
                                contract_start_date)),
                            until=parser.parse(str(current_date_to))))
                        for day in current_month_days:
                            if day.weekday() not in [5, 6]:
                                cur_month_weekdays += 1

                    elif contract_start_date <= current_date_from and \
                        contract_end_date <= current_date_to:
                        current_month_days = list(rrule.rrule(
                            rrule.DAILY, dtstart=parser.parse(str(
                                current_date_from)),
                            until=parser.parse(str(contract_end_date))))
                        for day in current_month_days:
                            if day.weekday() not in [5, 6]:
                                cur_month_weekdays += 1

            if cur_month_weekdays:
                new = {'code': 'TTLCURCONTDAY', 'name': 'Total current contract \
                            days in current month',
                       'number_of_days': cur_month_weekdays,
                       'sequence': 6, 'contract_id': contract_record.id}
                res.get('value').get('worked_days_line_ids').append(new)
            else:
                new = {'code': 'TTLCURCONTDAY', 'name': 'Total current\
                    contract days in current month', 'number_of_days': weekdays,
                       'sequence': 7, 'contract_id': contract_record.id}
                res.get('value').get('worked_days_line_ids').append(new)

            if self.employee_id.is_alternative_saturday:
                if self.date_from:
                    al_date_from = self.date_from
                else:
                    al_date_from = self._context.get('date_from', False)

                if self.date_to:
                    al_date_to = self.date_to
                else:
                    al_date_to = self._context.get('date_to', False)
                print("Date From", al_date_from, "Date To", al_date_to)
                qry = "select count(*) from alternative_working_days_line where date>= '"+str(al_date_from)+"' and date<'"+str(al_date_to)+"'"
                print(qry)
                self._cr.execute(qry)
                alternative_days = self._cr.dictfetchall()
                ad=""
                for rec in alternative_days:
                    ad = rec['count']
                print("AD", alternative_days, ad)
                new = {'code': 'AlternativeDays', 'name': 'Alternative Working\
                                    days in current month', 'number_of_days': ad,
                       'sequence': 6, 'contract_id': contract_record.id}
                res.get('value').get('worked_days_line_ids').append(new)

        if employee_id:
            emp_obj = self.env["hr.employee"]
            emp_rec = emp_obj.browse(employee_id)
            holiday_status_obj = self.env["hr.leave.type"]
            if emp_rec.leave_config_id:
                for h_staus in emp_rec.leave_config_id.holiday_group_config_line_ids:
                    flag = False
                    for payslip_data in res["value"].get("worked_days_line_ids"):
                        if payslip_data.get("code") == h_staus.leave_type_id.name:
                            if "name" in payslip_data:
                                payslip_data.update({
                                    "name": h_staus.leave_type_id.name2
                                })
                            flag = True
                    if not flag:
                        new = {'code': h_staus.leave_type_id.name,
                               'name': h_staus.leave_type_id.name2,
                               'number_of_days': 0.0, 'sequence': 0,
                               'contract_id': contract_record.id}
                        res.get('value').get(
                            'worked_days_line_ids').append(new)
            else:
                holidays_status_ids = holiday_status_obj.search([])
                for holiday_status in holidays_status_ids:
                    flag = False
                    for payslip_data in res["value"].get("worked_days_line_ids"):
                        if payslip_data.get("code") == holiday_status.name:
                            flag = True
                    if not flag:
                        new = {'code': holiday_status.name,
                               'name': holiday_status.name2,
                               'number_of_days': 0.0, 'sequence': 0,
                               'contract_id': contract_record.id}
                        res.get('value').get(
                            'worked_days_line_ids').append(new)

        return res

    def send_email_with_attachment(self):
        if not self.employee_id.work_email:
            raise Warning(_("Please add an email address for this employee in Employee>>Work Information>>Work Email"))
        payslip_id = self.env.ref('hr_payroll.action_report_payslip').render(self.id)
        data_record = base64.b64encode(payslip_id[0])
        ir_values = {
            'name': "Payslip",
            'type': 'binary',
            'datas': data_record,
            'store_fname': 'payslip_' + str(self.employee_id.name),
            'mimetype': 'application/x-pdf',
        }
        data_id = self.env['ir.attachment'].create(ir_values)
        email_values = {'email_to': self.employee_id.work_email,
                        'email_from': self.env.user.email}
        payslip_email = self.env.ref('teeni_payroll.email_payslip_template')
        payslip_email.attachment_ids = [(6, 0, [data_id.id])]
        payslip_email.send_mail(self.id, email_values=email_values, force_send=True)

        return True


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'
    _description = 'Payslip Batches'

    payroll_type = fields.Selection([('dep_wise', 'By Department'), ('company', 'By Company'), ('payment_type', 'By Payment Type')], default='dep_wise',
                                    string="Payslip Type")
    dept_id = fields.Many2one('hr.department', "Department")
    payment_mode = fields.Selection([('giro', 'Giro'), ('cash', 'Cash'), ('cheque', 'Cheque')])


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'
    _description = 'Generate payslips for all selected employees'

    def department(self):
        activ = self.env.context.get('active_ids')
        payslip_run = self.env['hr.payslip.run'].browse(activ)
        dep = payslip_run.dept_id
        print("dep", dep)
        return dep

    dept_id = fields.Many2one('hr.department', "Department", default=department)

    def def_payroll_type(self):
        activ = self.env.context.get('active_ids')
        payslip_run = self.env['hr.payslip.run'].browse(activ)
        type = payslip_run.payroll_type
        print("dep", type)
        return type

    payroll_type = fields.Selection(
        [('dep_wise', 'By Department'), ('company', 'By Company'), ('payment_type', 'By Payment Type')],
        default=def_payroll_type,
        string="Payslip Type")

    def def_payment_type(self):
        activ = self.env.context.get('active_ids')
        payslip_run = self.env['hr.payslip.run'].browse(activ)
        type = payslip_run.payment_mode
        print("dep", type)
        return type

    payment_mode = fields.Selection([('giro', 'Giro'), ('cash', 'Cash'), ('cheque', 'Cheque')], default=def_payment_type)

    def _get_domain(self):
        activ = self.env.context.get('active_ids')
        payslip_run = self.env['hr.payslip.run'].browse(activ)
        dep = payslip_run.dept_id
        print("depart", dep)
        if dep:
            return [('department_id', '=', dep.id)]
        else:
            return []

    employee_ids = fields.Many2many('hr.employee', 'hr_employee_group_rel', 'payslip_id', 'employee_id', 'Employees',
                                 )

    @api.onchange('dept_id')
    def on_change_department(self):
        if self.dept_id and self.payroll_type == "dep_wise":
            return {'domain': {'employee_ids': [('department_id', '=', self.dept_id.id)]}}
        elif self.payment_mode and self.payroll_type == "payment_type":
            return {'domain': {'employee_ids': [('payment_mode', '=', self.payment_mode)]}}
        else:
            return {'domain': {'employee_ids': []}}

    @api.onchange('payroll_type', 'dep_id', 'payment_mode')
    def add_employee(self):
        print("Change")
        emp_filter = []
        if self.payroll_type:
            if self.payroll_type == "dep_wise" and self.dept_id:
                emp_filter.append(tuple(['department_id', '=', self.dept_id.id]))
            if self.payroll_type == "payment_type":
                emp_filter.append(tuple(['payment_mode', '=', self.payment_mode]))
        emp = self.env['hr.employee'].search(emp_filter)
        lst = []
        for rec in emp:
            lst.append(rec.id)
        print("Emp List", lst)
        self.employee_ids = [(6, 0, lst)]

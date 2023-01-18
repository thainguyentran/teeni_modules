from odoo import models, fields, api


class HRContract(models.Model):
    _inherit = 'hr.contract'

    mobile_allowance = fields.Float()
    housing_allowance = fields.Float()
    cdac = fields.Boolean(string="CDAC")
    mbmf = fields.Boolean(string="MBMF")
    sinda = fields.Boolean(string="SINDA")

    def count_days(self, date_from, date_to):
        print(date_from, "<", self.date_start)
        if date_from < self.date_start:
            date_from = self.date_start

        if self.employee_id.cessation_date:
            if date_to > self.employee_id.cessation_date:
                date_to = self.employee_id.cessation_date

        if self.employee_id.identification_no:
            if self.employee_id.identification_no == "3" or self.employee_id.identification_no == "4":
                if date_from < self.employee_id.work_permit_start_date:
                    wpd = self.employee_id.work_permit_start_date
                    date_from = wpd

        day_date_from = date_from.day
        day_date_to = date_to.day
        work_day = day_date_to - day_date_from + 1

        print("WORK Day", work_day)
        return work_day

    def unused_leave(self, date_from, date_to):
        uul = 0
        work_month = 12
        start_month = 0
        if self.employee_id.cessation_date:
            if self.employee_id.cessation_date <= date_to:
                leave_type = self.env['hr.leave.type'].search([('name', '=', 'AL')])

                for rec in leave_type:
                    leave_days = rec.get_days(self.employee_id.id)[rec.id]
                    print("LD", leave_days)
                    uul = uul + leave_days["remaining_leaves"]
            if self.employee_id.cessation_date:
                if date_from.strftime('%Y') == self.date_start.strftime('%Y'):
                    start_month = int(self.date_start.strftime('%m'))-1

                if date_from.strftime('%m') == self.employee_id.cessation_date.strftime('%m') and date_to.strftime(
                    '%Y') == self.employee_id.cessation_date.strftime('%Y'):
                    work_month = int(date_from.strftime("%m"))
            work_month = work_month - start_month
            if work_month<=3:
                work_month = 0
            print('Count Month', work_month)
        return (uul/12)*work_month


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    employee_no = fields.Char()
    identification_no = fields.Selection([('1', 'Singaporean Citizen'), ('2', 'Permanent Resident'),
                                          ('3', 'S Pass.'),
                                          ('4', 'Work Permit'),
                                          ],
                                         string='2. ID Type of Employee')

    work_permit_start_date = fields.Date(string="Work Permit / Visa Start Date")
    payment_mode = fields.Selection([('giro', 'Giro'), ('cash', 'Cash'), ('cheque', 'Cheque')])
    cpf_included = fields.Boolean(string="CPF Included")
    leave_approve_rule = fields.Selection([('normal_staff', 'Normal Staff'),
                                           ('sale_staff', 'Sales Staff'),
                                           ('manager', 'Sales Executive and Managers')])
    is_alternative_saturday = fields.Boolean()

import time
from odoo import tools
from datetime import datetime
from dateutil.relativedelta import relativedelta as rv
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PayrollSummaryWizard(models.TransientModel):

    _inherit = 'payroll.summary.wizard'

    mode = fields.Selection([('company', 'By Company'), ('department', 'By Department'), ('employee', 'By Employee')], default="company")
    department_id = fields.Many2one('hr.department')
    employee_id = fields.Many2one('hr.employee')

    @api.onchange('mode', 'department_id', 'employee_id')
    def add_employee(self):
        print("Change")
        emp_filter = []
        if self.mode == "department":
            emp_filter.append(tuple(['department_id', '=', self.department_id.id]))
        if self.mode == "employee" :
            emp_filter.append(tuple(['id', '=', self.employee_id.id]))
        emp = self.env['hr.employee'].search(emp_filter)
        lst = []
        for rec in emp:
            lst.append(rec.id)
        print("Emp List", lst)
        self.employee_ids = [(6, 0, lst)]

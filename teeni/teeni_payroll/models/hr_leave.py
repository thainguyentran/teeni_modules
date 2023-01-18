
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HolidaysRequest(models.Model):
    _inherit = 'hr.leave'

    state = fields.Selection(selection_add=[('dept_confirm', 'Waiting For Department Manager Approve')])

    @api.multi
    def action_confirm(self):
        if self.filtered(lambda holiday: holiday.state != 'draft'):
            raise UserError(_('Leave request must be in Draft state ("To Submit") in order to confirm it.'))
        if self.employee_id.leave_approve_rule == "normal_staff":
            self.write({'state': 'dept_confirm'})
        else:
            self.write({'state': 'confirm'})
            self.activity_update()
        return True

    @api.multi
    def dept_confirm(self):
        print("DMID", self.employee_id.department_id.manager_id.user_id.id, "!=", self.env.uid )
        if self.employee_id.department_id.manager_id.user_id.id != self.env.uid:
            raise UserError(_('Only department manager can approve the leave'))
        self.write({'state': 'confirm'})
        self.activity_update()
        return True

    @api.multi
    def action_approve(self):
        context = self._context
        current_uid = context.get('uid')
        user = self.env.user
        # if validation_type == 'both': this method is the first approval approval
        # if validation_type != 'both': this method calls action_validate() below
        if self.employee_id.leave_approve_rule == "sale_staff" and not user.has_group('teeni_payroll.group_sale_supervisor'):
            raise UserError(_('Only Sale Supervisor/Executive can approve the leave'))
        if (self.employee_id.leave_approve_rule == "normal_staff" or self.employee_id.leave_approve_rule == "manager") and not user.has_group('teeni_inventory.group_operation_manager_rights'):
            raise UserError(_('Only director can approve the leave'))
        if any(holiday.state != 'confirm' for holiday in self):
            raise UserError(_('Leave request must be confirmed ("To Approve") in order to approve it.'))

        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        self.filtered(lambda hol: hol.validation_type == 'both').write({'state': 'validate1', 'first_approver_id': current_employee.id})
        self.filtered(lambda hol: not hol.validation_type == 'both').action_validate()
        if not self.env.context.get('leave_fast_create'):
            self.activity_update()
        return True

from openerp import fields, models
from datetime import datetime

class Leave_report(models.Model):
    _name = "emp.leave_report"

    leave_type = fields.Many2one('hr.holidays.status', string="Leave type")
    leave_status = fields.Selection([('confirm', 'To Approve'), ('validate', "Approved")], string="Status")
    leave_duration_type = fields.Selection([('short', "Short"), ('long', "Long")], string="Duration type")



    workers = fields.One2many('emp.leave_report.line', 'lv_id', string="Employees")


    def get_workers(self, cr, uid, ids, context=None):
        current_date = datetime.now().date()
        print current_date
        rec = self.browse(cr, uid, ids, context=None)
        rec = rec[0]
        rec.workers = None
        line_ids = []
        emp_ids = self.pool.get('hr.employee').search(cr, uid, [], context=None)
        for e in emp_ids:
            leaves_ids = self.pool.get('hr.holidays').search(cr, uid, [('employee_id', '=', e)], context=None)
            leaves = self.pool.get('hr.holidays').browse(cr, uid, leaves_ids, context=None)
            for l in leaves:
                from_date = (datetime.strptime(l.date_from, "%Y-%m-%d %H:%M:%S")).date()
                to_date = (datetime.strptime(l.date_to, "%Y-%m-%d %H:%M:%S")).date()
                go = True
                if from_date > current_date or to_date < current_date:
                    go = False
                    print "falsing 1"
                if rec.leave_duration_type and rec.leave_duration_type == 'short' and int(l.number_of_days_temp) > 30:
                    go = False
                    print "falsing 2"
                if rec.leave_duration_type and rec.leave_duration_type == 'long' and int(l.number_of_days_temp) <= 30:
                    go = False
                    print "falsing 3"
                if rec.leave_type.id and rec.leave_type.id != l.holiday_status_id.id:
                    go = False
                    print "falsing 4"
                if rec.leave_status and rec.leave_status == 'confirm' and l.state != 'confirm':
                    go = False
                    print "falsing 5"
                if rec.leave_status == 'validate' and l.state not in ['validate', 'validate1']:
                    go = False
                    print "falsing 6"
                remaining_days = (to_date-current_date).days

                if go:
                    vals = {
                        'name': l.employee_id.id,
                        'desc': l.name,
                        'state': l.state,
                        'start': l.date_from,
                        'end': l.date_to,
                        'total_days': l.number_of_days_temp,
                        'remaining_days': int(remaining_days)
                    }
                    line_ids.append(self.pool.get('emp.leave_report.line').create(cr, uid, vals, context=None))

        rec.workers = line_ids


class Leave_report_line(models.Model):
    _name = "emp.leave_report.line"

    name = fields.Many2one('hr.employee', string="Employee")
    desc = fields.Char(string="Description")
    state = fields.Char(string="State")
    start = fields.Datetime(string="Leave Start")
    end = fields.Datetime(string="Leave End")
    total_days = fields.Integer(string="Total days")
    remaining_days = fields.Integer(string="Days remaining")
    lv_id = fields.Integer(string="Leave report ID")

from openerp import tools
from openerp.osv import fields,osv
from openerp.addons.decimal_precision import decimal_precision as dp

class hr_timesheet_report(osv.osv):
    _name = "timesheet.report"
    _description = "Timesheet"
    _auto = False

    def _get_absent(self, cr, uid, context=None):

        print "IN GET ABSENT"
        return 1
    _columns = {
        'emp': fields.many2one('hr.employee', string="Employee", readonly=True),
        'department': fields.many2one('hr.department', string="department", readonly=True),
        'regular': fields.float('Regular', readonly=True),
        'overtime': fields.float('Overtime', readonly=True),
        'total': fields.float('Total', readonly=True),
        #'absent': fields.float('Absent'),
        'check_in': fields.date('Check_in', readonly=True)


    }

    _defaults = {
        'absent': _get_absent
    }

    def _select(self):
        select_str = """
             select min(a.id) as id, h.id as emp, c.id as department, sum(a.regular_float) as regular, sum(a.overtime_float) as overtime, sum(a.total) as total, DATE(a.check_in) as check_in
        """
        return select_str

    def _from(self):
        from_str = """
               hr_employee as h inner join emp_time_tracking as a on (h.id = a.name) left outer join hr_department as c on (c.id = h.department_id)
        """
        return from_str

    def _group_by(self):
        group_by_str = """
            group by h.id, c.id, DATE(a.check_in)
        """
        return group_by_str

    def init(self, cr):

        #self._table = timesheet_report
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM ( %s )
            %s
            )""" % (self._table, self._select(), self._from(), self._group_by()))

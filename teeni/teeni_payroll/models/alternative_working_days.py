import datetime

from odoo import models, fields, api
from datetime import datetime, date, timedelta


class AlternativeWorkingDays(models.Model):
    _name = 'alternative.working.days'

    name = fields.Char()
    year = fields.Selection([(num, str(num)) for num in range(2020, (datetime.now().year) + 2)], 'Year',
                            default=datetime.now().year, required=True)
    week_day = fields.Selection([('saturday', 'Saturday'), ('sunday', 'Sunday')], default="saturday", required="True")
    rec_lines = fields.One2many('alternative.working.days.line', 'alternative_day_id',
                                string="Alternative Working Days")

    _sql_constraints = [
        ('year_weekday_uniq', 'unique (year, week_day)', 'The combination of year and day of week must be unique !'),
    ]

    @api.model
    def create(self, vals):
        day_name = dict(self._fields['week_day'].selection).get(vals['week_day'])
        vals['name'] = day_name+'-'+ str(vals['year'])
        return super(AlternativeWorkingDays,self).create(vals)

    @api.multi
    def write(self, vals):
        wd = self.week_day
        year = self.year
        if 'week_day' in vals.keys():
            wd = vals['week_day']
        if 'year' in vals.keys():
            year = vals['year']
        day_name = dict(self._fields['week_day'].selection).get(wd)
        vals['name'] = day_name + '-' + str(year)
        return super(AlternativeWorkingDays, self).write(vals)

    @api.onchange('year', 'week_day')
    def get_alternative_days(self):
        print("FF", self.year, self.week_day)

        a = date(self.year, 1, 1)
        dt = date(self.year, 1, 1)
        d = datetime.combine(dt, datetime.min.time())
        print("D", dt, d)
        if(self.week_day == "saturday"):
            d += timedelta(days=5 - d.weekday())  # First Saturday
        else:
            d += timedelta(days=6 - d.weekday())  # First Sunday
        i = 0
        print("D1", d)
        list = [(5, 0, 0)]
        list.append((0, 0,{"date": d.date()}))
        while d.year == self.year:
            i = i + 1
            d += timedelta(days=7)
            # print("Loop", i, d, i%2)
            if i % 2 == 0 and d.year == self.year:
                print("Loop in", i, d)
                list.append((0, 0,{"date":d.date()}))

        print("All Date", list)

        self.rec_lines = list



class AlternativeWorkingDaysLine(models.Model):
    _name = 'alternative.working.days.line'

    alternative_day_id = fields.Many2one('alternative.working.days')
    date = fields.Date()
    day = fields.Char()

# coding: utf-8

import time
import datetime


from odoo import api, fields, models, exceptions, api, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    @api.multi
    def sale_order_line_copy(self):
        data = self.copy_data()
        for d in data:
            d.update({'order_id':self.order_id.id})
        if self.order_id.state == 'draft':
            sol_id = self.create(data[0])
            return {
               'type':'ir.actions.client',
               'tag':'reload',
         	}
        else:
            raise UserError(_('This sale order is not in draft state.'))
            	

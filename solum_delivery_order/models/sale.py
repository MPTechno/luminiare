from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang

import odoo.addons.decimal_precision as dp

class SalesOrders(models.Model):
    _inherit = 'sale.order'
    
    
    @api.multi
    def action_view_delivery(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        action = self.env.ref('stock.action_picking_tree_all').read()[0]

        pickings = self.mapped('picking_ids')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            print "\n\n===========Pickings",pickings
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        return action
        
'''class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    @api.multi
    def _prepare_order_line_procurement(self, group_id=False):
        self.ensure_one()
        print "\n\n=======self.order_id=",self.order_id,self.order_id.quote_type
        return {
            'name': self.name,
            'origin': self.order_id.name,
            'delivery_type':self.order_id.quote_type,
            'attention': self.order_id.attention,
            'crm_lead_id':self.order_id.crm_lead_id and self.order_id.crm_lead_id.id or False,
            'date_planned': datetime.strptime(self.order_id.date_order, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(days=self.customer_lead),
            'product_id': self.product_id.id,
            'product_qty': self.product_uom_qty,
            'product_uom': self.product_uom.id,
            'company_id': self.order_id.company_id.id,
            'group_id': group_id,
            'sale_line_id': self.id
        }'''
    

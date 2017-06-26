# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api

class SaleExtenstion(models.Model):
    _inherit = 'sale.order'
    
    quote_type = fields.Selection([
                                   ('led_strip','LED Strip Quotation'),
                                   ('led_atta_quote','LED Attachments Quotaion')
                                 ],string="Quotaion Type",readonly=True)
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('idle', 'Idle'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')
        
    state_when_idle = fields.Char(string="State when set Idle",readonly=True)
    
    state_change_date = fields.Date(string="State Change Date")
    
    def _calculateStateDays(self):
        diff_time = 0
        if self.state_change_date:
            current_date_str = fields.Date.context_today(self)
            current_date = fields.Date.from_string(current_date_str)
            state_change_str = self.state_change_date
            state_change = fields.Date.from_string(state_change_str)
            diff_time = (current_date - state_change).days
            if diff_time >= 7:
                self.write({'state':'idle'})
        self.days_sice_state_change = diff_time
    
    days_sice_state_change = fields.Integer(compute=_calculateStateDays,string="Days Since Last State")
    
    def set_to_active(self):
        return self.write({'state':self.state_when_idle})
        
    def set_to_idle(self):
        return self.write({'state':'idle','state_when_idle':self.state})
        
    @api.multi
    def write(self,vals):
        if vals.get('state',False):
            vals.update({'state_change_date':fields.Date.context_today(self)})
        return super(SaleExtenstion,self).write(vals)
        
class SaleOrderLineExtension(models.Model):
    _inherit = 'sale.order.line'
    
    image = fields.Binary(string="Image")
    
    unit_zero_text = fields.Text(string="Remarks")
                                 
            
    @api.multi
    @api.onchange('product_id')
    def onChnageProduct(self):
        if not self.product_id:
            self.update({
                'image': False,
            })
            return
        self.update({'image':self.product_id.image})

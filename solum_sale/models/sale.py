# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api

class SaleExtenstion(models.Model):
    _inherit = 'sale.order'
    
    @api.multi
    @api.depends('procurement_group_id')
    def _compute_picking_ids(self):
        for order in self:
            order.picking_ids = self.env['stock.picking'].search([('group_id', '=', order.procurement_group_id.id)]) if order.procurement_group_id else []
            order.delivery_count = len(order.picking_ids)

    
    @api.onchange('fiscal_position_id')
    def _compute_tax_id(self):
        """
        Trigger the recompute of the taxes if the fiscal position is changed on the SO.
        """
        for order in self:
            order.currency_id = self.env['res.currency'].search([('name', '=', 'SGD')])
            order.order_line._compute_tax_id()
    
    
    def _calculateStateDays(self):
        diff_time = 0
        if self.state_change_date and self.state in ('draft','sent'):
            current_date_str = fields.Date.context_today(self)
            current_date = fields.Date.from_string(current_date_str)
            state_change_str = self.state_change_date
            state_change = fields.Date.from_string(state_change_str)
            diff_time = (current_date - state_change).days
            if diff_time >= 7:
                self.write({'state':'idle'})
        self.days_sice_state_change = diff_time
    
    quote_type = fields.Selection([
                                   ('led_strip','LED Strip Quotation'),
                                   ('led_attach','LED Attachments Quotaion')
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
    attention = fields.Char("Attention")
    from_led_strip = fields.Char("From")
    name_led_strip = fields.Char("Name")
    email_led_strip = fields.Char("Email")
    state_change_date = fields.Date(string="State Change Date")
    crm_lead_id = fields.Many2one('crm.lead','Project')
    days_sice_state_change = fields.Integer(compute=_calculateStateDays,string="Days Since Last State")
    picking_ids = fields.Many2many('stock.picking', compute='_compute_picking_ids', string='Picking associated to this sale')
    delivery_count = fields.Integer(string='Delivery Orders', compute='_compute_picking_ids')
    remarks_ids = fields.One2many('sale.remarks','order_id','Remarks')
    
    
    def set_to_active(self):
        return self.write({'state':self.state_when_idle})
        
    def set_to_idle(self):
        return self.write({'state':'idle','state_when_idle':self.state})
        
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
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        return action
    
    @api.multi
    def write(self,vals):
        if vals.get('state',False):
            vals.update({'state_change_date':fields.Date.context_today(self)})
        return super(SaleExtenstion,self).write(vals)
        
class SaleOrderLineExtension(models.Model):
    _inherit = 'sale.order.line'
    
    
    @api.multi
    @api.depends('sequence', 'order_id')
    def get_number(self):
        for order in self.mapped('order_id'):
            number = 1
            for line in order.order_line:
                line.number = number
                number += 1
    
    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_id)
            net_price = 0.0
            if line.product_uom_qty > 0:
            	net_price = taxes['total_excluded'] / line.product_uom_qty
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
                'net_price': net_price,
            })
    
    
    net_price = fields.Monetary(compute='_compute_amount', string='Nett Price', readonly=True, store=True)
    image = fields.Binary(string="Image")
    unit_zero_text = fields.Text(string="Remarks")
    product_location_id = fields.Many2one('product.location','Location')
    length = fields.Char('Length(MM)')
    number = fields.Integer(compute='get_number', store=True ,string="Item")
                                 
    @api.multi
    @api.onchange('product_id')
    def onChnageProduct(self):
        if not self.product_id:
            self.update({
                'image': False,
            })
            return
        self.update({'image':self.product_id.image})
        
class ProductLocation(models.Model):
    _name = 'product.location'
    _description = 'Product Location'
    
    name = fields.Char(string='Location',required=True)

class SaleRemarks(models.Model):
    _name = 'sale.remarks'
    _description = 'Remarks'
    
    name = fields.Char(string='Remarks',required=True)
    order_id = fields.Many2one('sale.order','Sale Order')

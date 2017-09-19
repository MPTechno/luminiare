# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
import time
import datetime

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    delivery_type = fields.Selection([
                       ('led_strip','LED Strip Delivery Order'),
                       ('led_attach','LED Attachments Delivery Order'),
                       ('idesign','iDesign Delivery Order')
                     ],string="Delivery Type")
    sale_project_id = fields.Many2one('sale.project','Project')
    attention = fields.Char("Attention")
    remarks_ids = fields.One2many('picking.remarks','picking_id','Remarks')
    
    
    @api.model
    def get_line_length(self,obj):
        sale_order_pool = self.env['sale.order']
    	sale_order_ids = sale_order_pool.search([('name','=',obj.origin)])
        limit = 7
        line = sale_order_ids.order_line
        line_length = len(line)
        final_limit = limit - line_length
        if len(line) == 2:
            final_limit = final_limit - 1
        if len(line) == 3:
            final_limit = final_limit - 2
        if len(line) == 4:
            final_limit = final_limit - 3
        if len(line) == 5:
            final_limit = final_limit - 4
        if len(line) == 6:
            final_limit = final_limit - 5
        if len(line) == 7:
            final_limit = final_limit - 6
        if len(line) >= 8:
            final_limit = 22
        return final_limit
    
    def get_formated_date(self,min_date):
        if min_date:
            date = str(min_date).split(' ')
            date1 = datetime.datetime.strptime(date[0], '%Y-%m-%d')
            date2 = date1.strftime('%m/%d/%Y')
            return date2
        else:
        	return ''
    
    def get_order_remarks(self,obj):
    	sale_order_pool = self.env['sale.order']
    	sale_order_ids = sale_order_pool.search([('name','=',obj.origin)])
    	remarks_line_list = []
    	if sale_order_ids:
    		for line in sale_order_ids.remarks_ids:
    			remarks_line_list.append(line)
		return remarks_line_list
    
    def get_order_line(self,obj):
    	sale_order_pool = self.env['sale.order']
    	sale_order_ids = sale_order_pool.search([('name','=',obj.origin)])
    	order_line_list = []
    	if sale_order_ids:
    		for line in sale_order_ids.order_line:
    			order_line_list.append(line)
		return order_line_list
    
    @api.model
    def create(self, vals):
        sale_order_pool = self.env['sale.order']
        if vals.get('origin'):
        	sale_order_obj = sale_order_pool.search([('name','=',vals.get('origin'))])
        	if sale_order_obj:
        		vals.update({
        			'sale_project_id': sale_order_obj.sale_project_id and sale_order_obj.sale_project_id.id or False,
        			'attention': sale_order_obj.attention,
        			'delivery_type': sale_order_obj.quote_type,
        		})
        stock_picking_obj = super(StockPicking, self).create(vals)
        if vals.get('origin'):
            sale_order_obj = sale_order_pool.search([('name','=',vals.get('origin'))])
            
            picking_remarks_obj = self.env['picking.remarks']
            if sale_order_obj.quote_type == 'led_strip':
                remarks_ids = self.env['remarks.remarks'].search([('type','=','d_led_strip')])
                for remarks in remarks_ids:
	                picking_remarks_vals = {
	   	                'name': remarks and remarks.id or False,
	   	                'picking_id': stock_picking_obj and stock_picking_obj.id or False
	                }
	                picking_remarks_obj.create(picking_remarks_vals)
            if sale_order_obj.quote_type == 'led_attach':
                remarks_ids = self.env['remarks.remarks'].search([('type','=','d_led_attach')])
                for remarks in remarks_ids:
	                picking_remarks_vals = {
	   	                'name': remarks and remarks.id or False,
	   	                'picking_id': stock_picking_obj and stock_picking_obj.id or False
	                }
	                picking_remarks_obj.create(picking_remarks_vals)
            if sale_order_obj.quote_type == 'idesign':
                remarks_ids = self.env['remarks.remarks'].search([('type','=','idesign')])
                for remarks in remarks_ids:
	                picking_remarks_vals = {
	   	                'name': remarks and remarks.id or False,
	   	                'picking_id': stock_picking_obj and stock_picking_obj.id or False
	                }
	                picking_remarks_obj.create(picking_remarks_vals)
            
        return stock_picking_obj
        
class PickingRemarks(models.Model):
    _name = 'picking.remarks'
    _description = 'Picking Remarks'
    
    name = fields.Many2one('remarks.remarks','Remarks')
    picking_id = fields.Many2one('stock.picking','Picking')

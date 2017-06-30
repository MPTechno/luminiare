# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api

class InvoiceExtension(models.Model):
    _inherit = 'account.invoice'
    
    inv_type = fields.Selection([
                                   ('led_strip','LED Strip Invoice'),
                                   ('led_attach','LED Attachments Invoice')
                                 ],string="Invoice Type",readonly=True)
    attention = fields.Char("Attention")
    prepared_by = fields.Many2one("res.users",'Prepared By')
    approved_by = fields.Many2one("res.users",'Approved By')
    

class InvoiceLineExtension(models.Model):
    _inherit = 'account.invoice.line'
    
    location = fields.Char('Location')
    length = fields.Char('Length(MM)')
    
    inv_type = fields.Selection([
                                   ('led_strip','LED Strip Invoice'),
                                   ('led_attach','LED Attachments Invoice')
                                 ],string="Invoice Type",readonly=True)
    
    

# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api, _
from odoo.exceptions import UserError
class crm_lead(models.Model):
    _inherit = 'crm.lead'
    
    @api.depends('order_ids')
    def _compute_sale_amount_total(self):
        for lead in self:
            total = 0.0
            nbr = 0
            company_currency = lead.company_currency or self.env.user.company_id.currency_id
            sale_order_pool = self.env['sale.order']
            sale_order_ids = sale_order_pool.search([('crm_lead_id','=',lead.id)])
            for order in sale_order_ids:
                if order.state in ('draft', 'sent'):
                    nbr += 1
                if order.state not in ('draft', 'sent', 'cancel'):
                    #total += order.currency_id.compute(order.amount_untaxed, company_currency)
                    total += order.amount_total
            lead.sale_amount_total = total
            lead.sale_number = nbr
    
    @api.depends('stage_id')
    def _get_lead_state(self):
        for lead in self:
            if lead.stage_id:
                lead.update({'lead_state':lead.stage_id.name})
    
    @api.multi
    def action_open_lead_quotations(self):
        imd = self.env['ir.model.data']
        sale_order_pool = self.env['sale.order']
        sale_order_ids = sale_order_pool.search([('crm_lead_id','=',self.id)])
        if str(sale_order_ids.quote_type) == 'led_strip':
            action = imd.xmlid_to_object('solum_crm.sale_action_quotations_new_strip')
            form_view_id = imd.xmlid_to_res_id('solum_sale.view_led_strip_order_form')
            result = {
                'type': action.type,
                'views': [[form_view_id, 'form']],
                'context': self._context,
                'res_model': 'sale.order',
                'res_id': sale_order_ids.id 
            }
            return result
        elif str(sale_order_ids.quote_type) == 'led_attach':
            action = imd.xmlid_to_object('solum_crm.sale_action_quotations_new_attachment')
            form_view_id = imd.xmlid_to_res_id('solum_sale.view_led_attachment_order_form')
            result = {
                'type': action.type,
                'views': [[form_view_id, 'form']],
                'context': self._context,
                'res_model': 'sale.order',
                'res_id': sale_order_ids.id
            }
            return result
        else:
            raise UserError(_('There is no any quote for this opportunity !'))    
        
    
    @api.multi
    def quotations_new_attachment(self):
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('solum_crm.sale_action_quotations_new_attachment')
        form_view_id = imd.xmlid_to_res_id('solum_sale.view_led_attachment_order_form')
        result = {
                'type': action.type,
                'views': [[form_view_id, 'form']],
                'context': self._context,
                'res_model': 'sale.order',
                }
        partner_id = self.partner_id
        if partner_id:
            if partner_id.parent_id:
                context = self._context.copy()
                context.update({'default_partner_id':partner_id.parent_id.id, 'default_client_order_ref_id':partner_id.id})
                
                result.update({'context':context})
        return result
    @api.multi
    def quotations_new_strip(self):
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('solum_crm.sale_action_quotations_new_strip')
        form_view_id = imd.xmlid_to_res_id('solum_sale.view_led_strip_order_form')
        result = {
                'type': action.type,
                'views': [[form_view_id, 'form']],
                'context': self._context,
                'res_model': 'sale.order',
        }
        partner_id = self.partner_id
        if partner_id:
            if partner_id.parent_id:
                context = self._context.copy()
                context.update({'default_partner_id':partner_id.parent_id.id, 'default_client_order_ref_id':partner_id.id})
                result.update({'context':context})
        return result
    
    
    lead_state = fields.Char('Lead State', compute='_get_lead_state', store=True)
    

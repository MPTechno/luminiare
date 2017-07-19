# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api

class crm_lead(models.Model):
    _inherit = 'crm.lead'
    
    @api.depends('stage_id')
    def _get_lead_state(self):
        for lead in self:
            if lead.stage_id:
                lead.update({'lead_state':lead.stage_id.name})
    
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
                context.update({'default_partner_id':partner_id.parent_id.id})
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
                context.update({'default_partner_id':partner_id.parent_id.id})
                result.update({'context':context})
        return result
    
    
    lead_state = fields.Char('Lead State', compute='_get_lead_state', store=True)
    

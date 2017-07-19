# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.tools.translate import _
from datetime import datetime,tzinfo,timedelta
import time


class crm_to_quote_wizard(models.TransientModel):
    
    _name = 'crm.to.quote.wizard'
    
    quote_type = fields.Selection([('led_strip', 'LED Strip Quotation'),('led_attach', 'LED Attachment Quotation')], 'Quote Type', required=True, default='led_strip')
    
    
    @api.multi
    def quotations_new_attachment(self):
        lead_id = self._context.get('crm_lead_id',False)
        partner_id = self.env['crm.lead'].browse(lead_id).partner_id
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('solum_crm.sale_action_quotations_new_attachment')
        form_view_id = imd.xmlid_to_res_id('solum_sale.view_led_attachment_order_form')
        result = {
                'type': action.type,
                'views': [[form_view_id, 'form']],
                'context': self._context,
                'res_model': 'sale.order',
                }
        if partner_id:
            if partner_id.parent_id:
                context = self._context.copy()
                context.update({'default_partner_id':partner_id.parent_id.id})
                result.update({'context':context})
        return result
    @api.multi
    def quotations_new_strip(self):
        lead_id = self._context.get('crm_lead_id',False)
        partner_id = self.env['crm.lead'].browse(lead_id).partner_id
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('solum_crm.sale_action_quotations_new_strip')
        form_view_id = imd.xmlid_to_res_id('solum_sale.view_led_strip_order_form')
        result = {
                'type': action.type,
                'views': [[form_view_id, 'form']],
                'context': self._context,
                'res_model': 'sale.order',
        }
        if partner_id:
            if partner_id.parent_id:
                context = self._context.copy()
                context.update({'default_partner_id':partner_id.parent_id.id})
                result.update({'context':context})
        return result
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

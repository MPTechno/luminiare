# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api

class crm_lead(models.Model):
    _inherit = 'crm.lead'
    
    @api.depends('stage_id')
    def _get_lead_state(self):
        for lead in self:
            if lead.stage_id:
                lead.update({'lead_state':lead.stage_id.name})
    
    
    lead_state = fields.Char('Lead State', compute='_get_lead_state', store=True)
    

# -*- coding: utf-8 -*-
from odoo.osv.orm import setup_modifiers
from datetime import datetime
from dateutil.relativedelta import relativedelta
from lxml import etree
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError, AccessError
from odoo.tools.misc import formatLang
from odoo.addons.base.res.res_partner import WARNING_MESSAGE, WARNING_HELP
import odoo.addons.decimal_precision as dp

class res_partner(models.Model):
	_inherit = 'res.partner'

	opportunity_partner = fields.Boolean('Opportunity Partner')


class crm_lead(models.Model):
	_inherit = "crm.lead"

	@api.model
	def create(self, vals):
		res = super(crm_lead, self).create(vals)
		context = dict(self._context or {})
		if vals.get('type') and vals.get('type') == 'opportunity':
			res_partner = {
				'name':vals.get('name'),
				'email':vals.get('email_from'),
				'phone':vals.get('phone'),
				'opportunity_partner':True,
				'customer':False,
				'supplier':False,
				'company_type':'company',
				'is_company':True,
				'type':'contact',
			}
			partner_id = self.env['res.partner'].create(res_partner)
			res.write({'partner_id':partner_id and partner_id.id or False})
			
		return res 

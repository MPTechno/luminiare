# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import time
from werkzeug import exceptions, url_decode
from werkzeug.datastructures import Headers
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from odoo.http import Controller, route, request
from odoo.tools import html_escape
from odoo.addons.web.controllers.main import _serialize_exception, content_disposition
from odoo.tools.safe_eval import safe_eval

from odoo.addons.report.controllers.main import ReportController

class ReportController_SO(ReportController):
    #------------------------------------------------------
    # Report controllers
    #------------------------------------------------------
    @route(['/report/download'], type='http', auth="user")
    def report_download(self, data, token):
        """This function is used by 'qwebactionmanager.js' in order to trigger the download of
        a pdf/controller report.

        :param data: a javascript array JSON.stringified containg report internal url ([0]) and
        type [1]
        :returns: Response with a filetoken cookie and an attachment header
        """
        requestcontent = json.loads(data)
        url, type = requestcontent[0], requestcontent[1]
        try:
            if type == 'qweb-pdf':
                reportname = url.split('/report/pdf/')[1].split('?')[0]

                docids = None
                if '/' in reportname:
                    reportname, docids = reportname.split('/')

                if docids:
                    # Generic report:
                    response = self.report_routes(reportname, docids=docids, converter='pdf')
                else:
                    # Particular report:
                    data = url_decode(url.split('?')[1]).items()  # decoding the args represented in JSON
                    response = self.report_routes(reportname, converter='pdf', **dict(data))

                report = request.env['report']._get_report_from_name(reportname)
                filename = "%s.%s" % (report.name, "pdf")
                #Sale Order
                if report.report_name == 'solum_sale.sol_quotation_report_template_id':
                    so_pool = request.env['sale.order']
                    lst_so = []
                    lst_so = docids.split(",")
                    for ele_inv in lst_so:
                        so_obj = so_pool.browse([int(ele_inv)])
                        filename = so_obj.name +'-'+'Sol Luminaire'
                if report.report_name == 'solum_sale.idesign_quotation_report_template_id':
                    so_pool = request.env['sale.order']
                    lst_so = []
                    lst_so = docids.split(",")
                    for ele_inv in lst_so:
                        so_obj = so_pool.browse([int(ele_inv)])
                        filename = so_obj.name +'-'+'iDesign'
                #Invoice
                if report.report_name == 'solum_invoice.sol_invoice_report_template_id':
                    inv_pool = request.env['account.invoice']
                    lst_inv = []
                    lst_inv = docids.split(",")
                    for ele_inv in lst_inv:
                        inv_obj = inv_pool.browse([int(ele_inv)])
                        if inv_obj.number:
                            filename = inv_obj.number +'-'+'Sol Luminaire Customer'
                        else:
                            filename = inv_obj.partner_id.name +'-'+'Sol Luminaire Customer'
                if report.report_name == 'solum_invoice.idesign_invoice_report_template_id':
                    inv_pool = request.env['account.invoice']
                    lst_inv = []
                    lst_inv = docids.split(",")
                    for ele_inv in lst_inv:
                        inv_obj = inv_pool.browse([int(ele_inv)])
                        if inv_obj.number:
                            filename = inv_obj.number +'-'+'iDesign'
                        else:
                            filename = inv_obj.partner_id.name +'-'+'iDesign'
                if report.report_name == 'solum_invoice.sol_commission_invoice_report_template_id':
                    inv_pool = request.env['account.invoice']
                    lst_inv = []
                    lst_inv = docids.split(",")
                    for ele_inv in lst_inv:
                        inv_obj = inv_pool.browse([int(ele_inv)])
                        if inv_obj.number:
                            filename = inv_obj.number +'-'+'Sol Luminaire Commission'
                        else:
                            filename = inv_obj.partner_id.name +'-'+'Sol Luminaire Commission'
                #Delivery Order
                if report.report_name == 'solum_delivery_order.sol_do_report_template_id':
                    picking_pool = request.env['stock.picking']
                    lst_picking = []
                    lst_picking = docids.split(",")
                    for ele_picking in lst_picking:
                        picking_obj = picking_pool.browse([int(ele_picking)])
                        filename = picking_obj.name +'-'+'Sol Luminaire'
                if report.report_name == 'solum_delivery_order.idesign_do_report_template_id':
                    picking_pool = request.env['stock.picking']
                    lst_picking = []
                    lst_picking = docids.split(",")
                    for ele_picking in lst_picking:
                        picking_obj = picking_pool.browse([int(ele_picking)])
                        filename = picking_obj.name +'-'+'iDesign'
                filename = "%s.%s" % (filename, "pdf")
                if docids:
                    ids = [int(x) for x in docids.split(",")]
                    obj = request.env[report.model].browse(ids)
                    if report.print_report_name and not len(obj) > 1:
                        filename = safe_eval(report.print_report_name, {'object': obj, 'time': time})
                response.headers.add('Content-Disposition', content_disposition(filename))
                response.set_cookie('fileToken', token)
                return response
            elif type == 'controller':
                reqheaders = Headers(request.httprequest.headers)
                response = Client(request.httprequest.app, BaseResponse).get(url, headers=reqheaders, follow_redirects=True)
                response.set_cookie('fileToken', token)
                return response
            else:
                return
        except Exception, e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': "Odoo Server Error",
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))

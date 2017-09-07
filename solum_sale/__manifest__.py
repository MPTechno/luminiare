# -*- coding: utf-8 -*-
{
    "name": "Sol luminiare Sales Customization",
    "author": "HashMicro/ Amit",
    "version": "1.0",
    "website": "www.hashmicro.com",
    "category": "sale",
    "depends": ['product','sale','sales_team','web_readonly_bypass'],
    "data": [
        'security/ir.model.access.csv',
        'data/payment_term_data.xml',
        'data/remarks_data.xml',
		'views/sale_view.xml',
		'views/assets.xml',
		'views/report_menu.xml',
		'data/mail_template_data.xml',
		'report/sol_quotation_report_view.xml',
		'report/idesign_quotation_report_view.xml',
    ],
    "qweb": [
        'static/src/xml/widget.xml',
    ],
    'description': '''Sales Customization''',
    'demo': [],
    'installable': True,
    'auto_install': False,
}

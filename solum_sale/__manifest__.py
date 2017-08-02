# -*- coding: utf-8 -*-
{
    "name": "Sol luminiare Sales Customization",
    "author": "HashMicro/ Amit",
    "version": "1.0",
    "website": "www.hashmicro.com",
    "category": "sale",
    "depends": ['sale','sales_team'],
    "data": [
        'security/ir.model.access.csv',
        'data/payment_term_data.xml',
        'data/remarks_data.xml',
		'views/sale_view.xml',
		'views/assets.xml',
		'views/report_menu.xml',
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

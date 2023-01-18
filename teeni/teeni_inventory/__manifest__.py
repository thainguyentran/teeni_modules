# -*- coding: utf-8 -*-
{
    'name': "teeni_inventory",

    'summary': """
        Customized Module for inventoy functions based on Teeni's requests""",

    'description': """
        Customized Module for inventoy functions based on Teeni's requests
    """,

    'author': "TSW Technologies",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'stock', 'sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'security/user_rights.xml',
        'wizard/backorderlist_views.xml',
        'wizard/assign_driver_views.xml',
        'wizard/stock_picking_return_views.xml',
        'wizard/driver_report_views.xml',
        'wizard/stock_immediate_transfer_views.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/products.xml',
        'views/stock_inventory_views.xml',
        'reports/stock_picking.xml',
        'data/email_inventory_process_template.xml',
        'wizard/summary_picking_report.xml',


    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

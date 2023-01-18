# -*- coding: utf-8 -*-
{
    'name': "inventory_push_notification",

    'summary': """
            Push Notification for Inventory Operation""",

    'description': """
        Push Notification for Inventory Operations
    """,

    'author': "Appex",
    'website': "http://appex.co",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/11.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Sale',
    'version': '12.0.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'ocn_client'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/sale_push_notification_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

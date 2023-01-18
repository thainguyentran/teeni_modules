# -*- coding: utf-8 -*-
{
    'name': "teeni_acconting",

    'summary': """
        Customized module for accounting based on Teeni's request""",

    'description': """
        Customized module for accounting based on Teeni's request
    """,

    'author': "TSW Technologies",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account','teeni_crm','discount_total'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/credit_note.xml',
        'views/credit_note_with_item_and_price.xml',
        'views/credit_note_with_qty_only.xml',
        'views/supplier_grn.xml',
        'views/credit_note_in_base_currency.xml',
        'views/sales_journal.xml',
        'views/sales_journal_base_currency.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

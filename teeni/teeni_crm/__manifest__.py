# -*- coding: utf-8 -*-
{
    'name': "teeni_crm",

    'summary': """
        Teeni's customization for Sale, Purchase, Account and Stock module""",

    'description': """
        Teeni's customization for Sale, Purchase, Account and Stock module
    """,

    'author': "TSW Technologies",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'account','report_xlsx','purchase','stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/partner.area.csv',
        'data/account_payment_data.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/account_invoice_views.xml',
        'views/account_views.xml',
        'views/purchase_views.xml',
        'views/account_payment_views.xml',
        'reports/quotationprint.xml',
        'reports/purchase_report.xml',
        'reports/invoice_report.xml',
        'reports/payment_voucher_report.xml',
        'wizard/sales_report_views.xml',
        'wizard/sales_summary_report_views.xml',
        'wizard/profit_report.xml',
        'wizard/purchase_report_views.xml',
        'wizard/cu_yl_comp_report.xml',
        'wizard/sup_yl_comp_report.xml',
        'wizard/sup_monthly_payment_report.xml',
        'wizard/sup_sum_pur_report.xml',
        'wizard/cus_collection_report.xml',
        'wizard/cus_sales_report.xml',
        'wizard/invoice_analysis_report.xml',
        'wizard/cus_acc_act_report.xml',
        'wizard/stock_card_activity_report.xml',
        'wizard/gen_acc_act_report.xml',
        'wizard/sup_sum_aging_report.xml',
        'wizard/sup_detail_aging_report.xml',
        'wizard/cus_sum_aging_report.xml',
        'wizard/cus_detail_aging_report.xml',
        'views/invoice.xml',
        'wizard/sup_acc_act_report.xml',
        'views/Partner_Area.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

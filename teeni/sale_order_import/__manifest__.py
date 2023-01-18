
{
    'name': 'Sale Order Import',
    'version': '12.0.1.0.0',
    'category': 'Sale & Finance',
    'license': 'AGPL-3',
    'summary': 'Import pdf, xml file to sale order',
    'author': 'Appex',
    'website': 'https://appex.co',
    'depends': [
        'sale',
        'contacts',
        'base_iban',
        'base_business_document_import',
        'onchange_helper',
        'teeni_crm'
        ],
    'data': [
        'security/ir.model.access.csv',
        'security/rule.xml',
        'views/sale_order_import_config.xml',
        'views/res_config_settings.xml',
        'wizard/sale_order_import_view.xml',
        'views/partner.xml',
    ],
    'installable': True,
}

# -*- coding: utf-8 -*-
{
    'name': "Odoo CRM Commission Plan",
    'version': '18.0',
    'category': 'Sales',
    'description': """Odoo 18's CRM module features professional commission 
    plans that drive sales performance effectively.""",
    'author': "Cybrosys Techno Solutions",
    'company': "Cybrosys Techno Solutions",
    'depends': ['sale_management', 'crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/crm_commission_views.xml',
        'views/crm_team_views.xml',
        'views/res_users_views.xml',
        'wizard/commission_report_views.xml',
        'views/statement.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'commission_plan/static/src/js/action_manager.js',
        ],
    },
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}

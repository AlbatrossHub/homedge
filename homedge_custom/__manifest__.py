{
    'name': "Criyo Customization",
    'version': '18.0',
    'category': 'Sales',
    'summary': """Kriyo odoo18""",
    'description': """Odoo 18's CRM module features professional commission 
    plans that drive sales performance effectively.""",
    'author': 'Albatross IT Consultancy',
    'company': 'Albatross IT Consultancy',
    'website': "https://www.albatross.work",
    "depends": ['sale_management', 'crm'],
    'data': [
        'views/crm_team_views.xml',
        'views/sale_menus.xml'
        # 'data/lead_data.xml'
    ],
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}

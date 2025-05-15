# -*- coding: utf-8 -*-
{
    "name": "Additional Salesperson",
    'version': '18.0',
    "category": "CRM",
    "summary": """
        Additional Salesperson on Contact, Sale Order, and Opportunity""",
    "description": """
        You can add additional salesperson on Contact, Sale Order, or Opportunity. 
        For example, You can to assign salesperson assistant to responsible besides the salesperson itself.
    """,
    "images": ["static/description/thumbnail.png"],
    "depends": ["base", "sale", "crm"],
    "data": [
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/crm_lead_views.xml'
    ],
}

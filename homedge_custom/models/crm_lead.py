import json
import requests
import os

from datetime import datetime, timedelta
import pytz
from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class Partner(models.Model):
    _inherit = "res.partner"

    india_mart_query_id = fields.Char('India Mart Query ID')

class Lead(models.Model):
    _inherit = "crm.lead"


    inq_source = fields.Char('Source')
    india_mart_product_name = fields.Char('Product Interested in')
    india_mart_query_id = fields.Char('India Mart Query ID')
    lead_from_india_mart = fields.Boolean('India Mart Lead')
    co_one = fields.Many2one('res.partner', string="Care of (Primary)", tracking=True)
    co_two = fields.Many2one('res.partner', string="Care of (Secondary)", tracking=True)

    @api.model
    def _create_leads_form_india_mart(self):
        IST = pytz.timezone('Asia/Kolkata')
        end_time = datetime.now(IST)
        start_time = end_time - timedelta(hours=100)
        start_time_str = start_time.strftime("%d-%B-%Y%H:%M:%S")
        end_time_str = end_time.strftime("%d-%B-%Y%H:%M:%S")
        request_lead_url = "https://mapi.indiamart.com/wservce/crm/crmListing/v2/?glusr_crm_key=mRywFLhr4XrGT/ei43eK7luMpVbMmTdnXw==&start_time=%s&end_time=%s" % (start_time_str, end_time_str)
        print(request_lead_url)
        response = requests.get(request_lead_url).content
        dict_content = response.decode("UTF-8")
        datas = json.loads(dict_content)
        source = self.env.ref('crio_custom.utm_source_indiamart').id
        print(datas)
        if datas.get('CODE') == 200:
            inquiries = datas.get('RESPONSE')
            Lead = self.env['crm.lead']
            for data in inquiries:
                get_parnter = self.save_indiamart_lead_as_contact(data)
                if data.get('UNIQUE_QUERY_ID') and get_parnter:
                    vals = {
                        'type': 'opportunity',
                        'user_id': '1',
                        'partner_id': get_parnter.id if get_parnter.id else False,
                        'lead_from_india_mart': True,
                        'name': data.get('SUBJECT', 'Lead from IndiaMart'),
                        'email_from': data.get('SENDER_EMAIL', False),
                        'mobile': data.get('SENDER_MOBILE', False),
                        'phone': data.get('SENDER_PHONE', False),
                        'description': data.get('QUERY_MESSAGE', False),
                        'street': data.get('SENDER_ADDRESS', False),
                        'city': data.get('SENDER_CITY', False),
                        'state_id': get_parnter.state_id.id if get_parnter.state_id.id else False,
                        'country_id': get_parnter.country_id.id if get_parnter.country_id.id else False,
                        'contact_name': data.get('SENDER_NAME', False),
                        'partner_name': data.get('SENDER_COMPANY', False),
                        'india_mart_query_id': data.get('UNIQUE_QUERY_ID'),
                        'india_mart_product_name': data.get('QUERY_PRODUCT_NAME', False),
                        'inq_source': 'IndiaMart',
                        "source_id": source,
                    }
                    if not Lead.sudo().with_context(active_test=False).search([
                            ('india_mart_query_id', '=', data.get('UNIQUE_QUERY_ID')),
                            ('lead_from_india_mart', '=', True)], limit=1):
                        Lead.sudo().create(vals)
        return True

    def save_indiamart_lead_as_contact(self, data):
        contact_name = data.get('SENDER_NAME')
        create_parnter = False
        if contact_name == None or contact_name == False or contact_name == '' or not contact_name:
            contact_name = data.get('SENDER_COMPANY', False)
        Contact = self.env['res.partner']
        lead_country = self.env['res.country'].search([('code', '=', data.get('SENDER_COUNTRY_ISO'))], limit=1)
        lead_state = self.env['res.country.state'].search([('name', 'ilike', data.get('SENDER_STATE'))], limit=1)
        vals = {
            'name': contact_name,
            'phone': data.get('SENDER_PHONE', False),
            'mobile': data.get('SENDER_MOBILE', False),
            'street': data.get('SENDER_ADDRESS', False),
            'city': data.get('SENDER_CITY', False),
            'email': data.get('SENDER_EMAIL', False),
            'user_id': '1',
            'state_id': lead_state.id if lead_state.id else False,
            'country_id': lead_country.id if lead_country.id else False,
            'india_mart_query_id': data.get('UNIQUE_QUERY_ID'),
        }
        if not Contact.sudo().with_context(active_test=False).search([
                ('india_mart_query_id', '=', data.get('UNIQUE_QUERY_ID')),
                ], limit=1):
            create_parnter = Contact.sudo().create(vals)
            return create_parnter
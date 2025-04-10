from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    product_id = fields.Many2one("product.template", string="Product Prospect")
    prodict_image = fields.Image(string="Product Image")
    qty = fields.Integer(string="Qty Required")
    product_category = fields.Char(string="Product Category")
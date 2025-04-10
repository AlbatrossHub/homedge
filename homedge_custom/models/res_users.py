from odoo import fields, models


class ResUsers(models.Model):
    """Model res.users is inherited to add commission plan"""
    _inherit = 'res.users'

    commission_target = fields.Integer(string='Banchmark Target')

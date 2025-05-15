# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    add_user_ids = fields.Many2many("res.users")

    @api.onchange("partner_id")
    def onchange_partner2_id(self):
        self.add_user_ids = self.partner_id.add_user_ids

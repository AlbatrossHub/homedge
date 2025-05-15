# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    add_user_ids = fields.Many2many("res.users")


class SaleOrder(models.Model):
    _inherit = "sale.order"

    add_user_ids = fields.Many2many("res.users")

    @api.onchange("partner_id")
    def onchange_partner2_id(self):
        self.add_user_ids = self.partner_id.add_user_ids


class CrmLead(models.Model):
    _inherit = "crm.lead"

    add_user_ids = fields.Many2many("res.users")

    @api.model
    def create(self, vals):
        """Override create to ensure additional salespeople are set."""
        lead = super(CrmLead, self).create(vals)
        # If a partner is created or linked later, ensure salespeople are updated
        if lead.partner_id and lead.add_user_ids:
            lead.partner_id.write({"add_user_ids": [(6, 0, lead.add_user_ids.ids)]})
        return lead

    def write(self, vals):
        """Override write to update partner when additional salespeople change."""
        res = super(CrmLead, self).write(vals)
        if "add_user_ids" in vals or "partner_id" in vals:
            for lead in self:
                if lead.partner_id and lead.add_user_ids:
                    lead.partner_id.write(
                        {"add_user_ids": [(6, 0, lead.add_user_ids.ids)]}
                    )
        return res

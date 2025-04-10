# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#     Author: Arjun S(odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import io
import json

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import date_utils
from odoo.tools import json
from datetime import datetime, timedelta

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class CommissionReport(models.TransientModel):
    """The commission.report model is created and shown as the wizard window"""
    _name = 'commission.report'
    _description = 'Commission Report'

    date_from = fields.Date(string="From Date",
                            help="The date from report is needed")
    date_to = fields.Date(string="To Date", help="The date to report is needed")
    salesperson_ids = fields.Many2many('res.users', string='Salesperson(s)',
                                       domain="[('share','=',False)]",
                                       help="Salespersons of the corresponding "
                                            "reports")
    salesperson_id = fields.Many2one('res.users', string='A Salesperson (Summary)',
                                       domain="[('share','=',False)]",
                                       help="Salespersons of the corresponding "
                                            "reports")
    sales_team_ids = fields.Many2many('crm.team', string='Sales Team',
                                      help="Sales teams of the corresponding "
                                           "reports")
    date = fields.Date(string='Date', default=fields.Date.context_today,
                       help="Current date")
    is_sales_person = fields.Boolean(default=False, string="Is sales person",
                                     help="Whether the report is for sales "
                                          "person")
    is_sales_team = fields.Boolean(default=False, string="Is sales team",
                                   help="Whether the report is for sales team")

    @api.onchange('salesperson_ids')
    def _onchange_salesperson_ids(self):
        """Function for hide a field base on values"""
        self.is_sales_person = bool(self.salesperson_ids)

    @api.onchange('sales_team_ids')
    def _onchange_sales_team_ids(self):
        """Function for hide a field base on values"""
        self.is_sales_team = bool(self.sales_team_ids)

    @api.constrains('sales_team_ids', 'salesperson_ids')
    def sales_team_constrains(self):
        """Function for showing validation error"""
        for rec in self:
            if self.sales_team_ids:
                if not rec.sales_team_ids.member_ids:
                    raise ValidationError(_(
                        "Selected Sales Team haven't any Salespersons"))
                if not self.sales_team_ids.member_ids.commission_id and \
                        not self.sales_team_ids.commission_id:
                    raise ValidationError(_(
                        "Selected Sales Team haven't any Commission Plan"))
            elif self.salesperson_ids and not \
                    rec.salesperson_ids.commission_id:
                raise ValidationError(_(
                    "Selected Salesperson haven't any Commission Plan"))

    def action_print_xlsx_report(self):
        """Function for printing xlsx report"""
        # Salesperson's condition starts here
        user_sale_orders = self.env['sale.order'].search([
            ('user_id', 'in', self.salesperson_ids.ids)])
        total_list = []
        commission_list = []
        benchmark_commission_list = []
        final_commission_list = []
        user_commission_name = []
        user_commission_salesperson = []
        user_obj = user_sale_orders.mapped('user_id'). \
            sorted(key=lambda d: d.id)
        user_sale_orders_dict = {
            user: user_sale_orders.filtered(lambda rec: rec.user_id == user)
            for user in user_obj}
        for user, user_sale_orders in user_sale_orders_dict.items():
            commission_id = user.commission_id
            if not commission_id:
                continue
            if self.date_to and self.date_from:
                filtered_order_lines = user_sale_orders.filtered(
                    lambda rec: self.date_from <= rec.date_order.date()
                                <= self.date_to and rec.date_order.date()
                                >= commission_id.date_from
                ).mapped('order_line')
            elif not self.date_to and self.date_from:
                filtered_order_lines = user_sale_orders \
                    .filtered(lambda rec: rec.date_order.date() >=
                                          self.date_from >=
                                          commission_id.date_from) \
                    .mapped('order_line')
            elif self.date_to and not self.date_from:
                filtered_order_lines = user_sale_orders \
                    .filtered(lambda rec: rec.date_order.date() <=
                                          self.date_to <=
                                          commission_id.date_to) \
                    .mapped('order_line')
            else:
                filtered_order_lines = user_sale_orders.mapped(
                    'order_line')
            filtered_order_lines_commission_total = sum(
                filtered_order_lines.mapped('price_subtotal'))

            if commission_id.type == 'revenue' and \
                    commission_id.revenue_type == 'straight':
                if commission_id.straight_commission_type == 'percentage':
                    straight_commission = (
                        filtered_order_lines_commission_total
                        * commission_id.straight_commission_rate
                    ) / 100
                else:
                    straight_commission = commission_id.straight_commission_fixed
                commission_list.append(straight_commission)

                # Calculate Benchmark Target Commission
                benchmark_commission = (
                    user.commission_target * commission_id.straight_commission_rate
                ) / 100
                benchmark_commission_list.append(benchmark_commission)

                # Calculate Final Commission
                final_commission = straight_commission - benchmark_commission
                final_commission_list.append(final_commission)

                user_commission_name.append(commission_id.name)
                user_commission_salesperson.append(user.name)
                total_list.append(filtered_order_lines_commission_total)

        # Salesperson's condition ends here
        if not self.sales_team_ids and not self.salesperson_ids:
            self.sales_team_ids = self.env['crm.team'].search([])
        # Sales team's condition starts here
        team_sale_orders = self.env['sale.order'].search(
            [('team_id', 'in', self.sales_team_ids.ids)])
        team_obj = team_sale_orders.mapped('user_id'). \
            sorted(key=lambda d: d.id)
        team_sale_orders_dict = {
            team_user: self._filter_sale_orders_by_user(team_sale_orders,
                                                        team_user) for
            team_user in team_obj}
        commission_total, commission, commission_name, commission_salesperson, \
            commission_sales_team = self._calculate_commissions(
            team_sale_orders_dict
        )
        # Sales team's condition ends here
        data = {
            'model_id': self.id,
            'date': self.date,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'sales_team_ids': self.sales_team_ids.ids,
            'salesperson_ids': self.salesperson_ids.ids,
            'commission_list': commission_list,
            'benchmark_commission_list': benchmark_commission_list,
            'final_commission_list': final_commission_list,
            'total_list': total_list,
            'commission': commission,
            'commission_total': commission_total,
            'commission_name': commission_name,
            'commission_salesperson': commission_salesperson,
            'commission_sales_team': commission_sales_team,
            'user_commission_name': user_commission_name,
            'user_commission_salesperson': user_commission_salesperson,
        }
        return {
            'type': 'ir.actions.report',
            'data': {
                'model': 'commission.report',
                'options': json.dumps(data, default=date_utils.json_default),
                'output_format': 'xlsx',
                'report_name': 'Commission Plan xlsx report'},
            'report_type': 'xlsx'
        }

    def get_xlsx_report(self, data, response):
        """get_xlsx_report function"""
        date = data['date']
        team = data['sales_team_ids']
        user = data['salesperson_ids']
        commission_list = data['commission_list']
        total_list = data['total_list']
        commission = data['commission']
        commission_total = data['commission_total']
        commission_name = data['commission_name']
        commission_salesperson = data['commission_salesperson']
        commission_sales_team = data['commission_sales_team']
        user_commission_name = data['user_commission_name']
        user_commission_salesperson = data['user_commission_salesperson']
        benchmark_commission_list = data['benchmark_commission_list']
        final_commission_list = data['final_commission_list']
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({'align': 'center', 'bold': True,
                                    'font_size': '15px', 'valign': 'vcenter'})
        format1 = workbook.add_format({'align': 'left', 'font_size': '12px'})
        format2 = workbook.add_format({'align': 'right', 'font_size': '12x'})
        format3 = workbook.add_format(
            {'align': 'right', 'font_size': '12x', 'bold': True})
        heading = workbook.add_format({'align': 'left', 'bold': True,
                                       'font_size': '12px',
                                       'valign': 'vcenter'})
        date_format = workbook.add_format(
            {'num_format': 'dd/mm/yy', 'align': 'left', 'font_size': '10px'})
        sheet.merge_range('A2:B2', "Printed Date: " + date, date_format)
        sheet.write('A4', 'No.', heading)
        sheet.set_column(5, 1, 25)
        sheet.set_row(0, 25)
        row = 5
        col = 0
        index = 1
        if user:
            sheet.merge_range('A1:E1', 'COMMISSION PLAN REPORT', head)
            if data.get('date_from'):
                sheet.write('D2', 'Date From: ' + data['date_from'],
                            date_format)
            if data.get('date_to'):
                sheet.write('E2', 'Date To: ' + data['date_to'], date_format)
            sheet.write('B4', 'Sale Persons', heading)
            sheet.write('C4', 'Commission Plan Name', heading)
            sheet.write('D4', 'Total Revenue', heading)
            sheet.write('E4', 'Commission Amount', heading)
            sheet.write('F4', 'Benchmark Target Commission', heading)
            sheet.write('G4', 'Final Commission', heading)
            row = 5
            for benchmark, final in zip(benchmark_commission_list, final_commission_list):
                sheet.write(row, 5, round(benchmark, 2), format2)
                sheet.write(row, 6, round(final, 2), format2)
                row += 1
            for j in user_commission_salesperson:
                sheet.write(row, col + 0, index, format2)
                sheet.write(row, col + 1, j, format1)
                row += 1
                index += 1
            row = 5
            col = 0
            for j in user_commission_name:
                sheet.write(row, col + 2, j, format1)
                row += 1
            row = 5
            col = 0
            for j in total_list:
                sheet.write(row, col + 3, round(j, 2), format2)
                row += 1
            row = 5
            col = 0
            for i in commission_list:
                sheet.write(row, col + 4, round(i, 2), format2)
                row += 1
            sheet.write(row + 1, col + 2, 'Total', format3)
            sheet.write(row + 1, col + 3, round(sum(total_list), 2), format2)
            sheet.write(row + 1, col + 4, round(sum(commission_list), 2),
                        format2)
        elif team:
            sheet.merge_range('A1:F1', 'COMMISSION PLAN REPORT', head)
            if data.get('date_from'):
                sheet.write('E2', 'Date From: ' + data['date_from'],
                            date_format)
            if data.get('date_to'):
                sheet.write('F2', 'Date To: ' + data['date_to'], date_format)
            sheet.write('B4', 'Sales Teams', heading)
            sheet.write('C4', 'Sales Person', heading)
            sheet.write('D4', 'Commission Plan Name', heading)
            sheet.write('E4', 'Total Revenue', heading)
            sheet.write('F4', 'Commission Amount', heading)
            for j in commission_sales_team:
                sheet.write(row, col + 0, index, format2)
                sheet.write(row, col + 1, j, format1)
                row += 1
                index += 1
            row = 5
            col = 0
            for j in commission_salesperson:
                sheet.write(row, col + 2, j, format1)
                row += 1
            row = 5
            col = 0
            for j in commission_name:
                sheet.write(row, col + 3, j, format1)
                row += 1
            row = 5
            col = 0
            for j in commission_total:
                sheet.write(row, col + 4, round(j, 2), format2)
                row += 1
            row = 5
            col = 0
            for i in commission:
                sheet.write(row, col + 5, round(i, 2), format2)
                row += 1
            sheet.write(row + 1, col + 3, 'Total:', format3)
            sheet.write(row + 1, col + 4, round(sum(commission_total), 2),
                        format2)
            sheet.write(row + 1, col + 5, round(sum(commission), 2), format2)
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

    def _calculate_product_commission(self, filtered_order_lines,
                                      total_list, commission_list,
                                      user_commission_salesperson, *args):
        """Returns the calculated product commission"""
        user, commission_id, user_commission_name = args
        commission_products = commission_id.product_comm_ids.mapped(
            'product_id')
        commission_category = commission_id.product_comm_ids.mapped(
            'category_id')
        prod_commission = filtered_order_lines.filtered(
            lambda
                rec: rec.product_id.id in commission_products.ids or
                     rec.product_id.categ_id.id in commission_category.ids
        )
        for rule in commission_id.product_comm_ids:
            product_order_line = prod_commission.filtered(
                lambda rec: rec.product_id == rule.product_id or
                            rec.product_id.categ_id.id == rule.category_id.id)
            total_price = sum(product_order_line.mapped('price_subtotal'))
            product_commission = (total_price * rule.percentage) / 100 if \
                rule.commission_amount_type == 'percentage' else \
                rule.fixed_amount
            total_list.append(total_price)
            user_commission_name.append(commission_id.name)
            user_commission_salesperson.append(user.name)
            commission_list.append(
                rule.amount if product_commission > rule.amount and
                               rule.commission_amount_type == 'percentage'
                else product_commission
            )

    def _calculate_graduated_commission(self,
                                        commission_list,
                                        user_commission_salesperson,
                                        total_list, *args
                                        ):
        """Returns the calculated Graduated commission"""
        user, commission_id, rule, filtered_order_lines_commission_total, \
            user_commission_name = args
        graduated_commission = (
                                       filtered_order_lines_commission_total
                                       * rule.graduated_commission_rate
                               ) / 100 if rule.amount_from \
                                          <= filtered_order_lines_commission_total < rule.amount_to else \
            rule.graduated_fixed_amount
        commission_list.append(graduated_commission)
        user_commission_name.append(commission_id.name)
        user_commission_salesperson.append(user.name)
        total_list.append(filtered_order_lines_commission_total)

    def _calculate_straight_commission(self, commission_id,
                                       filtered_order_lines_commission_total,
                                       commission_list,
                                       *args):
        """Returns the calculated Straight commission"""
        user_commission_name, \
            user_commission_salesperson, total_list, user = args
        straight_commission = (
                                      filtered_order_lines_commission_total
                                      * commission_id.straight_commission_rate
                              ) / 100 if \
            commission_id.straight_commission_type == 'percentage' else \
            commission_id.straight_commission_fixed
        commission_list.append(straight_commission)
        user_commission_name.append(commission_id.name)
        user_commission_salesperson.append(user.name)
        total_list.append(filtered_order_lines_commission_total)

    def _filter_sale_orders_by_user(self, team_sale_orders, team_user):
        """Returns the filtered team_sale_orders using the team_users"""
        return team_sale_orders.filtered(lambda rec: rec.user_id == team_user)

    def _calculate_commissions(self, team_sale_orders_dict):
        """Returns the calculated commissions"""
        commission_total = []
        commission = []
        commission_name = []
        commission_salesperson = []
        commission_sales_team = []
        for team_user, team_sale_orders in team_sale_orders_dict.items():
            commissions_id = team_user.commission_id or \
                             team_user.sale_team_id.commission_id
            if commissions_id:
                if self.date_to and self.date_from:
                    filtered_order_lines = team_sale_orders.filtered(
                        lambda rec: self.date_from <= rec.date_order.date()
                                    <= self.date_to and rec.date_order.date()
                                    >= commissions_id.date_from
                    ).mapped('order_line')
                elif not self.date_to and self.date_from:
                    filtered_order_lines = team_sale_orders \
                        .filtered(lambda rec: rec.date_order.date() >=
                                              self.date_from >=
                                              commissions_id.date_from) \
                        .mapped('order_line')
                elif self.date_to and not self.date_from:
                    filtered_order_lines = team_sale_orders \
                        .filtered(lambda rec: rec.date_order.date() <=
                                              self.date_to <=
                                              commissions_id.date_to) \
                        .mapped('order_line')
                else:
                    filtered_order_lines = team_sale_orders.mapped(
                        'order_line')
                filtered_order_lines_commission_total = sum(
                    filtered_order_lines.mapped('price_subtotal'))
                if commissions_id.type == 'product':
                    commission_products = commissions_id.product_comm_ids.mapped(
                        'product_id').ids
                    commission_category = commissions_id.product_comm_ids.mapped(
                        'category_id').ids
                    prod_commission = filtered_order_lines.filtered(
                        lambda rec: rec.product_id.id in commission_products or
                                    rec.product_id.categ_id.id in commission_category
                    )
                    for rules in commissions_id.product_comm_ids:
                        product_order_line = prod_commission.filtered(
                            lambda rec: rec.product_id == rules.product_id or
                                        rec.product_id.categ_id.id == rules.category_id.id)
                        total_price = sum(
                            product_order_line.mapped('price_subtotal')
                        )
                        product_commission = (
                                                     total_price * rules.percentage
                                             ) / 100 if \
                            rules.commission_amount_type == 'percentage' else \
                            rules.fixed_amount
                        commission_total.append(total_price)
                        commission_name.append(commissions_id.name)
                        commission_salesperson.append(team_user.name)
                        commission_sales_team.append(
                            team_user.sale_team_id.name)
                        commission.append(
                            rules.amount if product_commission > rules.amount
                                            and rules.commission_amount_type == 'percentage'
                            else product_commission
                        )
                if commissions_id.type == 'revenue' and (
                        commissions_id.revenue_type == 'graduated'):
                    for rules in commissions_id.revenue_grd_comm_ids:
                        if rules.amount_from <= \
                                filtered_order_lines_commission_total \
                                < rules.amount_to:
                            graduated_commission = (
                                                           filtered_order_lines_commission_total
                                                           * rules.graduated_commission_rate) / 100 if \
                                rules.graduated_amount_type == 'percentage' \
                                else rules.graduated_fixed_amount
                            commission.append(graduated_commission)
                            commission_name.append(commissions_id.name)
                            commission_salesperson.append(team_user.name)
                            commission_sales_team.append(
                                team_user.sale_team_id.name)
                            commission_total.append(
                                filtered_order_lines_commission_total)
                if commissions_id.type == 'revenue' and (
                        commissions_id.revenue_type == 'straight'):
                    straight_commission = (
                                                  filtered_order_lines_commission_total
                                                  * commissions_id.straight_commission_rate
                                          ) / 100 if \
                        commissions_id.straight_commission_type == \
                        'percentage' else \
                        commissions_id.straight_commission_fixed
                    commission.append(straight_commission)
                    commission_name.append(commissions_id.name)
                    commission_salesperson.append(team_user.name)
                    commission_sales_team.append(team_user.sale_team_id.name)
                    commission_total.append(
                        filtered_order_lines_commission_total
                    )
        return commission_total, commission, commission_name, \
            commission_salesperson, commission_sales_team


    def print_package_bundle(self, internal=None):
        """
        Generate property invoice report for the agency partner by date range
        """
        if not self.date_from or not self.date_to:
            raise UserError(_("Please provide both Start Date and End Date."))
        property_invoices = self.env['sale.order'].search([
            ('user_id', '=', self.salesperson_id.id),
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to)
        ])
        statement_rows = []
        total_due_consolidated = 0
        target_comm = (self.salesperson_id.commission_target * self.salesperson_id.commission_id.straight_commission_rate) / 100
        for property_invoice in property_invoices:
            total_comm = (property_invoice.amount_untaxed * self.salesperson_id.commission_id.straight_commission_rate) / 100
            statement_rows.append({
                'invoice_name': property_invoice.name,
                'date_order': property_invoice.date_order.strftime('%d/%m/%Y') if property_invoice.date_order else 'N/A',
                'property_ref': property_invoice.partner_id.name,
                'quote_ref': property_invoice.name,
                'amount_total': property_invoice.amount_total,
                'property_address': property_invoice.partner_id.street,
                'gst': total_comm
            })
            total_due_consolidated += (property_invoice.amount_untaxed * self.salesperson_id.commission_id.straight_commission_rate) / 100
        final_val = total_due_consolidated - target_comm
        data = {
            'docs': self,
            'today_date': datetime.today().strftime('%d/%m/%Y'),  # Today's date
            'start_date': self.date_from.strftime('%d/%m/%Y'),  # Start date from the transient model
            'end_date': self.date_to.strftime('%d/%m/%Y'),  # End date from the transient model
            'agency': self.salesperson_id.name,
            'address': self.salesperson_id.street,
            'abn': self.salesperson_id.vat,
            'statement_rows': statement_rows,
            'total': "{:.2f}".format(total_due_consolidated),
            'target': "{:.2f}".format(target_comm),
            'final': "{:.2f}".format(final_val)
        }
        print(data)

        report = self.env.ref('commission_plan.report_account_move_action_agency_invoice_statement').report_action(self, data=data)
        return report

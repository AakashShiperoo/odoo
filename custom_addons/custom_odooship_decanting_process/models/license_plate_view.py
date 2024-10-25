# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import ValidationError



class LicensePlateOrders(models.Model):
    _name = 'license.plate.orders'
    _description = 'License Plate Model'

    name = fields.Char(string='License Plate Name')
    license_plate_order_line_ids = fields.One2many('license.plate.orders.line', 'license_plate_orders_id',
                               string='License Plate Lines')
    state = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], string='DR License Plate State', default='open')
    license_plate_state = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')], string='License Plate State')
    automation_manual = fields.Selection([('automation', 'Automation'),
                                          ('manual', 'Manual')], string='Automation Manual')
    delivery_receipt_order_id = fields.Many2one('delivery.receipt.orders',
                                                string='Delivery Receipt Order')
    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Receipt Order'
    )
    partner_id = fields.Many2one(related='picking_id.partner_id', string='Customer')
    tenant_code_id = fields.Many2one(
        'tenant.code.configuration',
        string='Tenant Code',
        related='partner_id.tenant_code_id',
        readonly=True
    )
    site_code_id = fields.Many2one('site.code.configuration',
                                   related='picking_id.site_code_id', string='Site Code')
    location_dest_id = fields.Many2one(related='picking_id.location_dest_id', string='Destination location')


    def action_open(self):
        for rec in self:
            rec.state = 'open'

    def check_and_update_license_plate_state(self):
        """
        Check if all lines in the license plate order have is_remaining_qty set to True.
        If they do, update the license_plate_state to 'not_available'.
        """
        all_remaining = all(line.is_remaining_qty for line in self.license_plate_order_line_ids)
        if all_remaining:
            self.license_plate_state = 'not_available'
        else:
            self.license_plate_state = 'available'

class LicensePlateOrdersLine(models.Model):
    _name = 'license.plate.orders.line'
    _description = 'License Plate Orders Line'

    name = fields.Char(string='Name')
    license_plate_orders_id = fields.Many2one('license.plate.orders', string='License Plate Orders', required=True, ondelete='cascade')
    sequence = fields.Integer(string="Sequence")
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float(string='Quantity', required=True)
    sku_code = fields.Char(string='SKU')
    state = fields.Selection([('open', 'Open'), ('closed', 'Closed')], string='State', default='open')
    remaining_qty = fields.Float('Remaining Quantity')
    is_remaining_qty = fields.Boolean(string='Remaining', default=False)

    def action_open_update_qty_wizard(self):
        """
        This method opens the wizard for updating the quantity.
        It passes the default picking_id and license_plate_orders_line_id to the context.
        """
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'update.qty.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_license_plate_orders_line_id': self.id,
                'default_picking_id': self.license_plate_orders_id.picking_id.id,  # Pass picking_id
            }
        }

    @api.depends('quantity')
    def _compute_remaining_qty(self):
        """
        Compute remaining quantity based on the quantity ordered (product_uom_qty)
        and the quantity done (quantity). Remaining qty is initially equal to available qty.
        """
        for move in self:
            # Initial remaining qty is the product_uom_qty (expected qty)
            move.remaining_qty = move.quantity

    def button_close_license_plate(self):
        """
        Close the license plate for this delivery receipt order line.
        """
        self.state = 'closed'


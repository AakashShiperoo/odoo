from odoo import models, fields, api
from odoo.exceptions import UserError
import json

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    message_log_ids = fields.One2many('inventory.message.log', 'picking_id', string='Message Logs')
    tag = fields.Selection([
        ('SLSU', 'Single Line Single Unit'),
        ('MLMU', 'Multi Line Multi Unit')
    ], string='Order Type Tag')
    virtual_location_id = fields.Many2one('stock.location', string='Virtual Location')
    pack_bench_id = fields.Many2one('stock.location', string='Pack Bench')
    hu_scanned = fields.Boolean(string='HU Scanned', default=False)
    hu_id = fields.Char(string='Handling Unit')
    hu_sequence = fields.Many2one('ir.sequence', string='HU Sequence')

    @api.model
    def create_hu_sequence(self):
        self.env['ir.sequence'].create({
            'name': 'Handling Unit Sequence',
            'code': 'handling.unit',
            'prefix': 'HU/',
            'padding': 5
        })

    @api.model
    def receive_hu_update(self, hu_data):
        picking = self.search([('hu_id', '=', hu_data['hu_id'])])
        if picking:
            picking.write({
                'state': 'done',
                'hu_id': hu_data['hu_id']
            })
        else:
            raise ValueError("Handling Unit not found.")

    def send_execution_message(self):
        for picking in self:
            message = {
                'picking_id': picking.id,
                'products': [{
                    'product_id': line.product_id.id,
                    'quantity': line.product_uom_qty
                } for line in picking.move_lines]
            }
            self.env['inventory.message.log'].create({
                'picking_id': picking.id,
                'message': json.dumps(message),
                'status': 'sent'
            })
            # Code to send message to external system (e.g., via API)
            # external_system.send_message(json.dumps(message))

    @api.model
    def receive_confirmation_message(self, message):
        for order_data in message.get('orders', []):
            picking = self.browse(order_data['picking_id'])
            if picking:
                picking.message_log_ids.create({
                    'picking_id': picking.id,
                    'message': 'Confirmation received',
                    'status': 'received',
                    'received_at': fields.Datetime.now()
                })
                picking.action_move_to_pack_station()

    def action_move_to_pack_station(self):
        self.ensure_one()
        self.write({'state': 'pack_station'})

    def start_packing_process(self):
        self.ensure_one()
        if not self.hu_scanned:
            self.write({'state': 'packing', 'hu_scanned': True})
            self.message_post(body="Started packing process")
        else:
            raise UserError("Packing process already started.")

    def scan_product_action(self):
        self.ensure_one()
        return {
            'name': 'Scan Product',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking.scan.product',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_picking_id': self.id}
        }

    def scan_virtual_location_action(self):
        self.ensure_one()
        return {
            'name': 'Scan Virtual Location',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking.scan.location',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_picking_id': self.id}
        }

    def scan_bag_id_action(self):
        self.ensure_one()
        return {
            'name': 'Scan Bag ID',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking.scan.bag',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_picking_id': self.id}
        }

    def scan_bag_id(self, bag_id):
        self.ensure_one()
        for line in self.move_lines:
            line.write({'state': 'done'})
        self.write({'state': 'pack_completed', 'bag_id': bag_id})

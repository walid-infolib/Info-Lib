from odoo import models, fields, api

from odoo.tools import float_is_zero


class StockMove(models.Model):
    _inherit = 'stock.move'

    price_unit = fields.Float(
        string='Unit Price', related="sale_line_id.price_unit")

    discount = fields.Float(
        string="Discount (%)",
        digits='Discount',
        related="sale_line_id.discount")

    tax_id = fields.Many2many('account.tax', string='Taxes', related="sale_line_id.tax_id")

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_currency_id',
        string="Currency",

    )

    price_subtotal = fields.Monetary(
        string="Subtotal",
        compute='_compute_price_subtotal',
        store=True,
        currency_field='currency_id',
    )
    price_tax = fields.Float(
        string="Total Tax",
        compute='_compute_price_subtotal',
        store=False,
        currency_field='currency_id',
    )

    price_total = fields.Monetary(
        string="Total",
        compute='_compute_price_subtotal',
        store=False,
        currency_field='currency_id',
    )

    @api.depends('sale_line_id.order_id.currency_id')
    def _compute_currency_id(self):
        """
        Compute the currency of the picking line.
        """
        for record in self:
            if record.sale_line_id:
                record.currency_id = record.sale_line_id.order_id.currency_id
            else:
                record.currency_id = record.company_id.currency_id

    @api.depends('quantity')
    def _compute_price_subtotal(self):
        """
        Compute the amounts of the picking line.
        """
        for line in self:
            tax_results = self.env['account.tax']._compute_taxes([
                line._convert_to_tax_base_line_dict()
            ], line.company_id)
            totals = list(tax_results['totals'].values())[0]
            amount_untaxed = totals['amount_untaxed']
            amount_tax = totals['amount_tax']

            price_subtotal_rounded = round(amount_untaxed, 2)
            price_total_rounded = round(amount_untaxed + amount_tax, 2)

            line.update({
                'price_subtotal': price_subtotal_rounded,
                'price_tax': amount_tax,
                'price_total': price_total_rounded,
            })

    def _convert_to_tax_base_line_dict(self, **kwargs):
        """ Convert the current record to a dictionary in move to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.sale_line_id.order_id.partner_id,
            currency=self.sale_line_id.order_id.currency_id,
            product=self.product_id,
            taxes=self.tax_id,
            price_unit=self.price_unit,
            quantity=self.quantity,
            discount=self.discount,
            price_subtotal=self.price_subtotal,
            **kwargs,
        )


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _get_aggregated_product_quantities(self, **kwargs):
        """ Returns a dictionary of products (key = id+name+description+uom+packaging) and corresponding values of interest.

        Allows aggregation of data across separate move lines for the same product. This is expected to be useful
        in things such as delivery reports. Dict key is made as a combination of values we expect to want to group
        the products by (i.e. so data is not lost). This function purposely ignores lots/SNs because these are
        expected to already be properly grouped by line.

        returns: dictionary {product_id+name+description+uom+packaging: {product, name, description, quantity, product_uom, packaging}, ...}
        """
        aggregated_move_lines = {}

        def get_aggregated_properties(move_line=False, move=False):
            move = move or move_line.move_id
            uom = move.product_uom or move_line.product_uom_id
            name = move.product_id.display_name
            description = move.description_picking
            if description == name or description == move.product_id.name:
                description = False
            product = move.product_id
            price_unit = move.price_unit
            discount = move.discount
            tax_id = move.tax_id
            price_subtotal = move.price_subtotal

            line_key = f'{product.id}_{product.display_name}_{description or ""}_{uom.id}_{move.product_packaging_id or ""}_{tax_id}'
            return (
                line_key, name, description, uom, move.product_packaging_id, price_unit, discount, tax_id,
                price_subtotal)

        def _compute_packaging_qtys(aggregated_move_lines):
            # Needs to be computed after aggregation of line qtys
            for line in aggregated_move_lines.values():
                if line['packaging']:
                    line['packaging_qty'] = line['packaging']._compute_qty(line['qty_ordered'], line['product_uom'])
                    line['packaging_quantity'] = line['packaging']._compute_qty(line['quantity'], line['product_uom'])
            return aggregated_move_lines

        # Loops to get backorders, backorders' backorders, and so and so...
        backorders = self.env['stock.picking']
        pickings = self.picking_id
        while pickings.backorder_ids:
            backorders |= pickings.backorder_ids
            pickings = pickings.backorder_ids

        for move_line in self:
            if kwargs.get('except_package') and move_line.result_package_id:
                continue
            line_key, name, description, uom, packaging, price_unit, discount, tax_id, price_subtotal = get_aggregated_properties(
                move_line=move_line)
            quantity = move_line.product_uom_id._compute_quantity(move_line.quantity, uom)
            if line_key not in aggregated_move_lines:
                qty_ordered = None
                if backorders and not kwargs.get('strict'):
                    qty_ordered = move_line.move_id.product_uom_qty
                    # Filters on the aggregation key (product, description and uom) to add the
                    # quantities delayed to backorders to retrieve the original ordered qty.
                    following_move_lines = backorders.move_line_ids.filtered(
                        lambda ml: get_aggregated_properties(move=ml.move_id)[0] == line_key
                    )
                    qty_ordered += sum(following_move_lines.move_id.mapped('product_uom_qty'))
                    # Remove the done quantities of the other move lines of the stock move
                    previous_move_lines = move_line.move_id.move_line_ids.filtered(
                        lambda ml: get_aggregated_properties(move=ml.move_id)[0] == line_key and ml.id != move_line.id
                    )
                    qty_ordered -= sum(
                        [m.product_uom_id._compute_quantity(m.quantity, uom) for m in previous_move_lines])
                aggregated_move_lines[line_key] = {
                    'name': name,
                    'description': description,
                    'quantity': quantity,
                    'qty_ordered': qty_ordered or quantity,
                    'product_uom': uom,
                    'product': move_line.product_id,
                    'packaging': packaging,
                    'price_unit': price_unit,
                    'discount': discount,
                    'tax_id': tax_id,
                    'price_subtotal': price_subtotal,
                }
            else:
                aggregated_move_lines[line_key]['qty_ordered'] += quantity
                aggregated_move_lines[line_key]['quantity'] += quantity

        # Does the same for empty move line to retrieve the ordered qty. for partially done moves
        # (as they are splitted when the transfer is done and empty moves don't have move lines).
        if kwargs.get('strict'):
            return _compute_packaging_qtys(aggregated_move_lines)
        pickings = (self.picking_id | backorders)
        for empty_move in pickings.move_ids:
            if not (empty_move.state == "cancel" and empty_move.product_uom_qty
                    and float_is_zero(empty_move.quantity, precision_rounding=empty_move.product_uom.rounding)):
                continue
            line_key, name, description, uom, packaging, price_unit, price_subtotal, discount, tax_id = get_aggregated_properties(
                move=empty_move)

            if line_key not in aggregated_move_lines:
                qty_ordered = empty_move.product_uom_qty
            aggregated_move_lines[line_key] = {
                'name': name,
                'description': description,
                'quantity': False,
                'qty_ordered': qty_ordered,
                'product_uom': uom,
                'product': empty_move.product_id,
                'packaging': packaging,
                'price_unit': price_unit,
                'discount': discount,
                'tax_id': tax_id,
                'price_subtotal': price_subtotal,
            }
        else:
            aggregated_move_lines[line_key]['qty_ordered'] += empty_move.product_uom_qty

        return _compute_packaging_qtys(aggregated_move_lines)

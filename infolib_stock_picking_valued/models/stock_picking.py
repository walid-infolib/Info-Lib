from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    delivery_report_valued = fields.Boolean(
        related='partner_id.delivery_report_valued',
    )

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_currency_id',
    )
    amount_untaxed = fields.Monetary(string="Untaxed Amount", currency_field='currency_id', store=True,
                                     compute='_compute_amounts')
    amount_tax = fields.Monetary(string="Taxes", currency_field='currency_id', store=True, compute='_compute_amounts')
    amount_total = fields.Monetary(string="Total", currency_field='currency_id', store=True, compute='_compute_amounts')

    tax_totals = fields.Binary(compute='_compute_tax_totals', exportable=False)

    @api.depends('move_ids.sale_line_id.order_id.currency_id')
    def _compute_currency_id(self):
        for record in self:
            if record.sale_id:
                record.currency_id = record.sale_id.currency_id
            else:
                record.currency_id = record.company_id.currency_id

    @api.depends('move_ids_without_package.quantity')
    def _compute_amounts(self):
        """Compute the total amounts of the picking."""
        for picking in self:
            if picking.company_id.tax_calculation_rounding_method == 'round_globally':
                tax_results = self.env['account.tax']._compute_taxes([
                    line._convert_to_tax_base_line_dict()
                    for line in picking.move_ids_without_package
                ])
                totals = tax_results['totals']
                amount_untaxed = totals.get(picking.currency_id, {}).get('amount_untaxed', 0.0)
                amount_tax = totals.get(picking.currency_id, {}).get('amount_tax', 0.0)
            else:
                amount_untaxed = sum(picking.move_ids_without_package.mapped('price_subtotal'))
                amount_tax = sum(picking.move_ids_without_package.mapped('price_tax'))

            picking.amount_untaxed = amount_untaxed
            picking.amount_tax = amount_tax
            picking.amount_total = picking.amount_untaxed + picking.amount_tax

    @api.depends_context('lang')
    @api.depends('move_ids_without_package.quantity')
    def _compute_tax_totals(self):
        for picking in self:
            lines = picking.move_ids_without_package
            picking.tax_totals = self.env['account.tax']._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in lines],
                picking.currency_id or picking.company_id.currency_id,
            )

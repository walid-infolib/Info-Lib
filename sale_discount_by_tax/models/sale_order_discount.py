# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import models, _


class SaleOrderDiscount(models.TransientModel):
    _inherit = 'sale.order.discount'

    def _create_discount_lines(self):
        """Create SO lines according to wizard configuration"""
        self.ensure_one()

        # Check if the discount product is defined in the company settings. If not, create it.
        discount_product = self.company_id.sale_discount_product_id
        if not discount_product:
            self.company_id.sale_discount_product_id = self.env['product.product'].create(
                self._prepare_discount_product_values()
            )
            discount_product = self.company_id.sale_discount_product_id

        # Treat differently depending on whether the discount is a fixed amount or a percentage.
        if self.discount_type == 'amount':

            total_price_per_tax_groups = defaultdict(
                float)  # Initialize a dictionary to store the total price_subtotal per tax group.
            # If there is no product or quantity to sell it will go out
            for line in self.sale_order_id.order_line:
                if not line.product_uom_qty or not line.price_unit:
                    continue

                # Calculate total price_subtotal by tax group.
                total_price_per_tax_groups[line.tax_id] += line.price_subtotal

            if not total_price_per_tax_groups:
                # If there are no valid rows to apply the discount to, terminate the function.
                return

            elif len(total_price_per_tax_groups) == 1:
                # If all lines have the same taxes, apply the discount globally.

                taxes = next(iter(
                    total_price_per_tax_groups.keys()))  # Gives us the first tax found in the dict because there is only one

                subtotal = total_price_per_tax_groups[
                    taxes]  # Gives us the sum of price before tax for each type of tax

                # Calculation of the discount percentage for each tax group
                discount_percentage_for_group = (self.discount_amount / (
                        subtotal + subtotal * sum(taxes.mapped('amount')) / 100)) * 100

                vals_list = [{
                    **self._prepare_discount_line_values(
                        product=discount_product,
                        amount=subtotal * discount_percentage_for_group / 100,
                        taxes=taxes,
                        description=_("Discount: %(percent)s%%", percent=discount_percentage_for_group)
                    ),
                }]
            else:
                vals_list = []
                total_subtotal = sum(total_price_per_tax_groups.values())  # Sum of all perice subtotal same
                # If different lines have different taxes, create a discount line for each tax group.
                for tax, subtotal in total_price_per_tax_groups.items():
                    weight = subtotal / total_subtotal  # Weighting of each tax group.

                    amount_discount_for_group = self.discount_amount * weight  # Discount amount per tax group


                    # Calculation of the discount percentage for each tax group
                    discount_percentage_for_group = (amount_discount_for_group / (
                            subtotal + (subtotal * tax.amount / 100))) * 100

                    vals_list.append(
                        self._prepare_discount_line_values(
                            product=discount_product,
                            amount=subtotal * discount_percentage_for_group / 100,
                            taxes=tax,
                            description=_(
                                "Discount: %(percent)s%%"
                                "- On products with the following taxes %(taxes)s",
                                percent=discount_percentage_for_group,
                                taxes=tax.name
                            ),
                        )
                    )


        else:  # so_discount
            # For a percentage discount, calculate the discount by tax group.
            total_price_per_tax_groups = defaultdict(
                float)  # Initialize a dictionary to store the total price_subtotal per tax group.
            for line in self.sale_order_id.order_line:
                if not line.product_uom_qty or not line.price_unit:
                    continue

                # Calculate total price_subtotal by tax group.
                total_price_per_tax_groups[line.tax_id] += line.price_subtotal

            if not total_price_per_tax_groups:
                # If there are no valid rows to apply the discount to, terminate the function.
                return
            elif len(total_price_per_tax_groups) == 1:
                # If all lines have the same taxes, apply the discount globally.
                taxes = next(iter(total_price_per_tax_groups.keys()))
                subtotal = total_price_per_tax_groups[taxes]
                vals_list = [{
                    **self._prepare_discount_line_values(
                        product=discount_product,
                        amount=subtotal * self.discount_percentage,
                        taxes=taxes,
                        description=_(
                            "Discount: %(percent)s%%",
                            percent=self.discount_percentage * 100
                        ),
                    ),
                }]
            else:
                # If different lines have different taxes, create a discount line for each tax group.
                vals_list = [
                    self._prepare_discount_line_values(
                        product=discount_product,
                        amount=subtotal * self.discount_percentage,
                        taxes=taxes,
                        description=_(
                            "Discount: %(percent)s%%"
                            "- On products with the following taxes %(taxes)s",
                            percent=self.discount_percentage * 100,
                            taxes=", ".join(taxes.mapped('name'))
                        ),
                    ) for taxes, subtotal in total_price_per_tax_groups.items()
                ]
        return self.env['sale.order.line'].create(vals_list)

# Developed by Info'Lib. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError

from .. import const

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(
        selection_add=[('konnect', "Konnect")],
        ondelete={'konnect': 'set default'}
    )


    #=== CREDENTIALS FIELDS ===#

    konnect_wallet_key = fields.Char(
        string="Konnect Wallet Key",
        help="Copy the wallet key from the Konnect organisation dashboard.",
        required_if_provider='konnect',
        groups='base.group_system'
    )

    konnect_api_key = fields.Char(
        string="Konnect Api Key",
        help="Generate an api key from the Konnect organisation dashboard.",
        required_if_provider='konnect',
        groups='base.group_system'
    )


    # === CONFIGURATIONS FIELDS ===#

    lifespan = fields.Integer(
        string="Lifespan",
        default=10,
        help="Duration before the payment expires, in minutes.",
        required_if_provider='konnect'
    )

    payment_fees = fields.Boolean(
        string="Payment Fees",
        default=False,
        help="Ask the client to pay an extra amount to cover Konnect fees. This will slightly raise the amount of the payment from the payer side.",
        groups='base.group_system'
    )

    checkout_form = fields.Boolean(
        string="Checkout Form",
        default=False,
        help="Ask the payer to fill a checkout form before payment.",
        groups='base.group_system'
    )

    silent_webhook = fields.Boolean(
        string="Silent Webhook",
        default=False,
        help="If this is true, Konnect will make the call to the webhook without redirecting the payer to the webhook URL.",
        groups='base.group_system'
    )

    theme = fields.Selection(
        string='Theme',
        selection=const.THEME,
        default='light',
        required_if_provider='konnect',
        groups='base.group_system'
    )

    type = fields.Selection(
        string='Transaction Type',
        selection=const.TRANSACTION_TYPE,
        default='immediate',
        required_if_provider='konnect',
        groups='base.group_system'
    )

    transaction_description = fields.Text(
        string='Transaction Description',
        default='Payment made by an Odoo website.',
        required_if_provider='konnect',
        groups='base.group_system'
    )


    # === ACTION METHODS ===#

    def _konnect_get_api_url(self):
        """
        Returns the API URL for Konnect based on the current state.

        :return: API URL as a string.
        """
        self.ensure_one()
        return (
            "https://api.preprod.konnect.network/api/v2/payments/"
            if self.state == 'test'
            else "https://api.konnect.network/api/v2/payments/"
        )


    #=== CONSTRAINT METHODS ===#

    @api.constrains('transaction_description')
    def _check_transaction_description_length(self):
        for record in self:
            if len(record.transaction_description) < 3 or len(record.transaction_description) > 280:
                raise ValidationError("The field 'Transaction Description' must have a length between 3 and 280 characters.")

# Developed by Info'Lib. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models, fields, api

from .. import const

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('konnect', "Konnect")],
        ondelete={'konnect': 'set default'}
    )

    # Credentials
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

    # Configurations
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
        string='Transaction type',
        selection=const.TRANSACTION_TYPE,
        default='immediate',
        required_if_provider='konnect',
        groups='base.group_system'
    )

    description = fields.Text(
        string='Description',
        default='Payment made by an Odoo website.',
        required_if_provider='konnect',
        groups='base.group_system'
    )

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

# Developed by Info'Lib. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    #=== FIELDS ===#

    code = fields.Selection(
        selection_add=[('flouci', "Flouci")],
        ondelete={'flouci': 'set default'}
    )

    #=== FIELDS - CREDENTIALS ===#

    flouci_app_token = fields.Char(
        string="App Token",
        help="Copy the public token generated on the developers api platform.",
        required_if_provider='flouci',
        groups='base.group_system'
    )

    flouci_app_secret = fields.Char(
        string="App Secret",
        help="Copy the private token generated on the developers api platform.",
        required_if_provider='flouci',
        groups='base.group_system'
    )

    #=== FIELDS - CONFIGURATIONS ===#

    accept_card = fields.Boolean(
        string="Accept Card",
        default=True,
        groups='base.group_system'
    )

    session_timeout = fields.Integer(
        string="Session Timeout",
        help="Payment session duration in seconds",
        default=1200,
        groups='base.group_system'
    )

    #=== CONSTRAINT METHODS ===#

    @api.constrains('session_timeout')
    def _check_session_timeout(self):
        for record in self:
            if record.code == "flouci" and record.session_timeout < 60:
                _logger.warning("The session timeout must be greater or equal than 60 seconds.")
                raise ValidationError("The session timeout must be greater or equal than 60 seconds.")

    #=== BUSINESS METHODS - GETTERS ===#

    def _flouci_get_base_url(self):
        """
        Returns the BASE URL for Flouci based on the current state.

        :return: BASE URL as a string.
        """
        self.ensure_one()
        return (
            "https://developers.flouci.com/api/"
            if self.state == 'test'
            else "https://developers.flouci.com/api/"
        )

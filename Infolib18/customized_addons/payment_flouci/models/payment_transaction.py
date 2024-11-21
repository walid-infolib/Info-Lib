# Developed by Info'Lib. See LICENSE file for full copyright and licensing details.

import logging
import requests

from werkzeug import urls

from odoo import _, models, fields, api
from odoo.exceptions import ValidationError

from odoo18.odoo.api import Transaction
from ..controllers.main import FlouciController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    #=== FIELDS ===#

    developer_tracking_id = fields.Char(
        string="Developer Tracking Id",
        readonly=True,
        compute='_compute_developer_tracking_id'
    )

    # === COMPUTE METHODS ===#

    @api.model
    def _compute_developer_tracking_id(self):
        self.ensure_one()
        if self.provider_id and self.provider_id.code == 'flouci':
            tracking_id = self.env['ir.sequence'].next_by_code('payment.transaction')
            _logger.info("Generated Developer Tracking Id: %s", tracking_id)
            self.developer_tracking_id = tracking_id
        else:
            _logger.error("No valid provider code or provider_id is not set.")
            self.developer_tracking_id =  None

    # === BUSINESS METHODS - PAYMENT FLOW ===#

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Flouci-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'flouci':
            return res

        api_url = self._flouci_get_api_url("generate_payment")
        headers = {
            'Content-Type': 'application/json'
        }

        _logger.info("Preparing to generate a flouci payment.")

        webhook_url = urls.url_join(self.provider_id.get_base_url(), FlouciController._webhook_url)

        payload = {
            'app_token': self.provider_id.flouci_app_token,
            'app_secret': self.provider_id.flouci_app_secret,
            'amount': int(self.amount * (1 / self.currency_id.rounding)),
            'success_link': webhook_url,
            'fail_link': webhook_url,
            'developer_tracking_id': self.developer_tracking_id,
            'session_timeout_secs': self.provider_id.session_timeout,
            'accept_card': self.provider_id.accept_card
        }

        _logger.info("Payload sent to Flouci API: %s", payload)

        try:
            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            response_data = response.json()
        except requests.exceptions.RequestException as e:
            _logger.error("Request to Flouci API failed: %s", e)
            print(e.response.json())
            raise ValidationError(_("Failed to generate payment with Flouci. Please try again later."))
        except ValueError:
            _logger.error("Invalid response from Flouci API: %s", response.text)
            raise ValidationError(_("Received invalid response from Flouci payment provider. Please contact support."))

        _logger.info("Response data from Flouci API: %s", response_data)

        payment_id = response_data.get('result').get('payment_id')
        if not payment_id:
            errors = response_data.get('message', 'Error creating Flouci transaction')
            _logger.error("Failed to create Flouci transaction: %s", errors)
            raise ValidationError(errors)

        self.provider_reference = payment_id

        _logger.info("Successfully generate Flouci transaction. Payment Provider reference: %s", payment_id)

        link = response_data.get('result').get('link')
        return {
            'api_url': link,
            'payment_id': payment_id
        }

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on dummy data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The dummy notification data
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'flouci' or len(tx) == 1:
            return tx

        provider_reference = notification_data.get('payment_id')
        tx = self.search([('provider_reference', '=', provider_reference), ('provider_code', '=', 'flouci')])
        if not tx:
            raise ValidationError(
                "Flouci: " + _("No transaction found matching provider reference %s.", provider_reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Update the transaction state and the provider reference based on the notification data.

        This method should usually not be called directly. The correct method to call upon receiving
        notification data is :meth:`_handle_notification_data`.

        For a provider to handle transaction processing, it must overwrite this method and process
        the notification data.

        Note: `self.ensure_one()`

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'flouci':
            return

        _logger.info("Processing Flouci notification data: %s", notification_data)

        if not notification_data:
            _logger.error("The customer left the Flouci payment page.")
            self._set_canceled(_("The customer left the Flouci payment page."))
            return

        provider_reference = notification_data.get('payment_id')
        api_url = self._flouci_get_api_url(f"verify_payment/{provider_reference}") if provider_reference else None

        headers = {
            'Content-Type': 'application/json',
            'apppublic': self.provider_id.flouci_app_token,
            'appsecret': self.provider_id.flouci_app_secret
        }

        try:
            response = requests.get(
                api_url,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            response_data = response.json()
        except requests.exceptions.RequestException as e:
            _logger.error("Request to Flouci API failed: %s", e)
            self._set_error(_("There was an issue contacting the payment provider. Please try again later."))
            return
        except ValueError:
            _logger.error("Invalid response from Flouci API: %s", response.text)
            self._set_error(_("Received invalid response from the payment provider. Please contact support."))
            return

        _logger.info("Response data from Flouci API: %s", response_data)

        payment_status = response_data.get('result').get('status')
        if not payment_status:
            _logger.error("Payment status is missing from the response. Please contact support.")
            self._set_error(_("Payment status is missing from the response. Please contact support."))
        elif payment_status == "SUCCESS":
            _logger.info("Payment completed successfully. Thank you!")
            self._set_done(_("Payment completed successfully. Thank you!"))
            self._set_done()
        elif payment_status == "FAILURE":
            _logger.error("Payment has failed. Please try again later or contact our support team.")
            self._set_error(_("Payment has failed. Please try again later or contact our support team."))
        else:
            _logger.error("Unknown payment status received: %s. Please contact support." % payment_status)
            self._set_error(_("Unknown payment status received: %s. Please contact support." % payment_status))

    #=== BUSINESS METHODS - GETTERS ===#

    def _flouci_get_api_url(self, endpoint):
        """
        Construct the full API URL for Flouci.

        This method generates the complete API URL by appending the specified endpoint
        to the base URL obtained from the provider. The provider is accessed with sudo
        permissions to ensure the method can retrieve the correct base URL.

        :param str endpoint: The API endpoint to be appended to the base URL.
        :return: The full API URL as a string.
        :rtype: str
        """
        if self.provider_code != 'flouci':
            return

        provider_sudo = self.provider_id.sudo()
        base_api_url = provider_sudo._flouci_get_base_url()
        return f"{base_api_url}{endpoint}"

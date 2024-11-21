# Developed by Info'Lib. See LICENSE file for full copyright and licensing details.

import logging
import requests

from werkzeug import urls

from urllib.parse import urlparse, parse_qs

from odoo import _, models
from odoo.exceptions import ValidationError

from .. import const
from ..controllers.main import KonnectController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    #=== BUSINESS METHODS - PAYMENT FLOW ===#

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Konnect-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'konnect':
            return res

        api_url = self._konnect_get_api_url("init-payment")
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': self.provider_id.konnect_api_key,
        }

        _logger.info("Preparing to send payment initialization request to Konnect API.")

        webhook_url = urls.url_join(self.provider_id.get_base_url(), KonnectController._webhook_url)

        payload = {
            'receiverWalletId': self.provider_id.konnect_wallet_key,
            'token': self.currency_id.name,
            'amount': int(self.amount * (1 / self.currency_id.rounding)),
            'type': self.provider_id.type,
            'description': self.provider_id.description,
            'acceptedPaymentMethods': self._get_accepted_payment_methods(),
            'lifespan': self.provider_id.lifespan,
            'checkoutForm': self.provider_id.checkout_form,
            'addPaymentFeesToAmount': self.provider_id.payment_fees,
            'firstName': self.partner_name,
            'lastName': '',
            'phoneNumber': self.partner_phone,
            'email': self.partner_email,
            'orderId': self.reference,
            'webhook': webhook_url,
            'silentWebhook': self.provider_id.silent_webhook,
            'successUrl': webhook_url,
            'failUrl': webhook_url,
            'theme': self.provider_id.theme
        }

        _logger.info("Payload sent to Konnect API: %s", payload)

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
            _logger.error("Request to Konnect API failed: %s", e)
            raise ValidationError(_("Failed to initialize payment with Konnect. Please try again later."))
        except ValueError:
            _logger.error("Invalid response from Konnect API: %s", response.text)
            raise ValidationError(_("Received invalid response from Konnect payment provider. Please contact support."))

        _logger.info("Response data from Konnect API: %s", response_data)

        payment_ref = response_data.get('paymentRef')
        if not payment_ref:
            errors = response_data.get('errors', 'Error creating Konnect transaction')
            _logger.error("Failed to create Konnect transaction: %s", errors)
            raise ValidationError(errors)

        self.provider_reference = payment_ref

        _logger.info("Successfully initializing Konnect transaction. Payment provider reference: %s", payment_ref)

        api_url = response_data['payUrl']
        return {
            'api_url': api_url,
            'payment_ref': payment_ref,
            'theme': self.provider_id.theme,
            'mdOrder': self._get_md_order(api_url)
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
        if provider_code != 'konnect' or len(tx) == 1:
            return tx

        provider_reference = notification_data.get('provider_reference')
        tx = self.search([('provider_reference', '=', provider_reference), ('provider_code', '=', 'konnect')])
        if not tx:
            raise ValidationError(
                "Konnect: " + _("No transaction found matching provider reference %s.", provider_reference)
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
        if self.provider_code != 'konnect':
            return

        _logger.info("Processing Konnect notification data: %s", notification_data)

        if not notification_data:
            _logger.error("The customer left the Konnect payment page.")
            self._set_canceled(_("The customer left the Konnect payment page."))
            return

        provider_reference = notification_data.get('payment_ref')
        api_url = self._konnect_get_api_url(provider_reference) if provider_reference else None

        try:
            response = requests.get(
                api_url,
                timeout=30
            )
            response.raise_for_status()
            response_data = response.json()
        except requests.exceptions.RequestException as e:
            _logger.error("Request to Konnect API failed: %s", e)
            self._set_error(_("There was an issue contacting the payment provider. Please try again later."))
            return
        except ValueError:
            _logger.error("Invalid response from Konnect API: %s", response.text)
            self._set_error(_("Received invalid response from the payment provider. Please contact support."))
            return

        _logger.info("Response data from konnect API: %s", response_data)

        payment_status = response_data.get('payment').get('status')
        if not payment_status:
            _logger.error("Payment status is missing from the response. Please contact support.")
            self._set_error(_("Payment status is missing from the response. Please contact support."))
        elif payment_status == "completed":
            _logger.info("Payment completed successfully. Thank you!")
            self._set_done(_("Payment completed successfully. Thank you!"))
        elif payment_status == "pending":
            failed_transactions = response_data.get('payment').get('failedTransactions')
            if failed_transactions and failed_transactions == 1:
                _logger.error("Payment has failed. Please try again later or contact our support team.")
                self._set_error(_("Payment has failed. Please try again later or contact our support team."))
            else:
                _logger.error("Payment is currently pending. Please complete the payment.")
                self._set_pending(_("Payment is currently pending. Please complete the payment."))
        else:
            _logger.error("Unknown payment status received: %s. Please contact support." % payment_status)
            self._set_error(_("Unknown payment status received: %s. Please contact support." % payment_status))

    #=== BUSINESS METHODS - GETTERS ===#

    def _get_accepted_payment_methods(self):
        """
        Retrieve the accepted payment methods based on the current payment method.

        This method checks the currently selected payment method for the transaction and returns
        a list of accepted payment methods specific to that payment method. If no specific payment
        method is selected or if the payment method code is unknown, it returns a default list
        of accepted payment methods defined in `const.ACCEPTED_PAYMENT_METHODS`.

        :return: A list of accepted payment methods for the transaction.
        :rtype: list
        """
        self.ensure_one()
        if self.payment_method_id and self.payment_method_id.code:
            code = self.payment_method_id.code
            if code == 'bank_card':
                return ['bank_card']
            elif code == 'e-dinar':
                return ['e-DINAR']
            elif code == 'wallet':
                return ['wallet']
            elif code == 'flouci':
                return ['flouci']
            else:
                return const.ACCEPTED_PAYMENT_METHODS
        else:
            return const.ACCEPTED_PAYMENT_METHODS

    def _konnect_get_api_url(self, endpoint):
        """
        Construct the full API URL for Konnect.

        This method generates the complete API URL by appending the specified endpoint
        to the base URL obtained from the provider. The provider is accessed with sudo
        permissions to ensure the method can retrieve the correct base URL.

        :param str endpoint: The API endpoint to be appended to the base URL.
        :return: The full API URL as a string.
        :rtype: str
        """
        if self.provider_code != 'konnect':
            return

        provider_sudo = self.provider_id.sudo()
        base_api_url = provider_sudo._konnect_get_base_url()
        return f"{base_api_url}{endpoint}"

    def _get_md_order(self, url):
        """
        Extracts the mdOrder value from the given URL.

        :param url: The URL containing the mdOrder parameter.
        :return: The value of mdOrder or None if not found.
        """
        # Parse the URL
        parsed_url = urlparse(url)

        # Get the query parameters
        query_params = parse_qs(parsed_url.query)

        # Extract the mdOrder value
        return query_params.get('mdOrder', [None])[0]

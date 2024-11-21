# Developed by Info'Lib. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class KonnectController(http.Controller):
    _webhook_url = '/payment/konnect/webhook/'

    @http.route(_webhook_url, type='http', auth='public', methods=['GET'], csrf=False)
    def konnect_webhook(self, **raw_data):
        """ Process the notification data sent by Konnect to the webhook.

        See https://www.pronamic.nl/wp-content/uploads/2013/04/BPE-3.0-Gateway-HTML.1.02.pdf.

        :param dict raw_data: The un-formatted notification data
        :return: An empty string to acknowledge the notification
        :rtype: str
        """

        _logger.info("Notification received from Konnect with data:\n%s", raw_data)

        # Normalize data keys to ensure consistency
        data = self._normalize_data_keys(raw_data)

        # Extract the payment reference from the normalized data
        payment_ref = data.get('payment_ref')
        if not payment_ref:
            _logger.error("Payment reference missing in webhook data.")
            return request.redirect('/shop/cart')  # Redirecting to the chart for bad request if no payment_ref

        # Search for the transaction using the payment reference
        transaction = request.env['payment.transaction'].sudo().search([('reference', '=', payment_ref)], limit=1)

        if transaction:
            # Process the notification data for the found transaction
            transaction._handle_feedback_data('konnect', data)
        else:
            # Log an error if the transaction is not found
            _logger.error("No transaction found for payment reference: %s", payment_ref)
            return request.redirect('/shop/cart')  # Redirecting to the chart for bad request if no transaction created
        return request.redirect('/payment/status')  # Redirecting to the payment status

    @staticmethod
    def _normalize_data_keys(data):
        """ Set all keys of a dictionary to lower-case.

        As Konnect parameters names are case insensitive, we can convert everything to lower-case
        to easily detected the presence of a parameter by checking the lower-case key only.

        :param dict data: The dictionary whose keys must be set to lower-case
        :return: A copy of the original data with all keys set to lower-case
        :rtype: dict
        """
        return {key.lower(): val for key, val in data.items()}

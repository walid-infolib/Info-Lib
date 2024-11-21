# Developed by Info'Lib. See LICENSE file for full copyright and licensing details.

import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class FlouciController(http.Controller):
    _webhook_url = '/payment/flouci/webhook/'

    @http.route(_webhook_url, type='http', auth='public', methods=['GET'], csrf=False)
    def flouci_webhook(self, **raw_data):
        """ Process the notification data sent by Flouci to the webhook.

        See https://www.pronamic.nl/wp-content/uploads/2013/04/BPE-3.0-Gateway-HTML.1.02.pdf.

        :param dict raw_data: The un-formatted notification data
        :return: An empty string to acknowledge the notification
        :rtype: str
        """

        _logger.info("Notification received from Flouci with data:\n%s", raw_data)

        # Normalize data keys to ensure consistency
        data = self._normalize_data_keys(raw_data)

        # Extract the payment provider reference from the normalized data
        payment_id = data.get('payment_id')
        if not payment_id:
            _logger.error("Payment_id missing in webhook data.")
            return request.redirect('/shop/cart')  # Redirecting to the chart for bad request if no payment_id

        # Search for the transaction using the payment provider reference
        transaction = request.env['payment.transaction'].sudo().search([('provider_reference', '=', payment_id)], limit=1)

        if transaction:
            # Process the notification data for the found transaction
            transaction._handle_notification_data('flouci', data)
        else:
            # Log an error if the transaction is not found
            _logger.error("No transaction found for payment_id: %s", payment_id)
            return request.redirect('/shop/cart')  # Redirecting to the chart for bad request if no transaction created

        return request.redirect('/payment/status')  # Redirecting to the payment status

    @staticmethod
    def _normalize_data_keys(data):
        """ Set all keys of a dictionary to lower-case.

        As Flouci parameters names are case insensitive, we can convert everything to lower-case
        to easily detected the presence of a parameter by checking the lower-case key only.

        :param dict data: The dictionary whose keys must be set to lower-case
        :return: A copy of the original data with all keys set to lower-case
        :rtype: dict
        """
        return {key.lower(): val for key, val in data.items()}

# Developed by Info"Lib. See LICENSE file for full copyright and licensing details.
{
    "name": "Konnect Payment Acquirer",
    "version": "2.0",
    "author": "Info'Lib",
    "category": "Accounting/Payment Acquirers",
    "summary": "A tunisian payment acquirer.",
    "description": " ",  # Non-empty string to avoid loading the README file.
    "depends": ["payment"],
    "data": [
        "views/payment_konnect_templates.xml",
        "views/payment_views.xml",

        "data/payment_icon_data.xml",
        "data/payment_acquirer_data.xml",
    ],
    'uninstall_hook': 'uninstall_hook',
    "images": [
        "static/description/banner.png"
    ],
    "license": "LGPL-3",
}

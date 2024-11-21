# Developed by Info"Lib. See LICENSE file for full copyright and licensing details.
{
    "name": "Payment Provider: Konnect",
    "version": "2.0",
    "author": "Info'Lib",
    "category": "Accounting/Payment Providers",
    "summary": "A tunisian payment provider.",
    "description": " ",  # Non-empty string to avoid loading the README file.
    "depends": ["payment"],
    "data": [
        "views/payment_konnect_templates.xml",
        "views/payment_provider_views.xml",

        "data/payment_method_data.xml",
        "data/payment_provider_data.xml",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "images": [
        "static/description/banner.png"
    ],
    "license": "LGPL-3",
}

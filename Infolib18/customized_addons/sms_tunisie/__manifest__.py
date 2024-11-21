{
    "name": "Tunisie SMS",
    "version": "18.0.0.0.0",
    "depends": ["sms", "iap"],
    "excludes": ["iap_alternative_provider"],
    "author": "Info'Lib",
    "description": "Tunisie SMS"
                   " you can integrate sms_tunisie into your interface by simply clicking on the installer button",
    "license": "AGPL-3",
    'website': "https://www.infolib.tn/",

    "data": [
        "views/iap_account_views.xml",
        "views/sms_composer_views.xml",
        "views/sms_sms_view.xml",
    ],
    "active": False,
    "installable": True,
    'images': ['static/description/Banner.png']

}

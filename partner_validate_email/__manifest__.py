{
    "name": "Validate Email",
    'version': '17.0.0.0.0',
    "author": "Info'Lib",
    "website": "https://www.infolib.tn/",
    'category': 'Localization',
    'description': """
Check if an email is valid, properly formatted and really exists
============================================
    """,
    'depends': ['base'],
    "external_dependencies": {"python": ["validate_email", "py3DNS"]},
    "data": [
        "data/ir_action_data.xml",
    ],
    'installable': True,
    "license": "LGPL-3",
    "images": [
        "images/infolib_tn.png",
        ],
}

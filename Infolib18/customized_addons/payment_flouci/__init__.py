# Developed by Info'Lib. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers

from odoo.addons.payment import setup_provider, reset_payment_provider


def post_init_hook(env):
    setup_provider(env, 'flouci')


def uninstall_hook(env):
    reset_payment_provider(env, 'flouci')

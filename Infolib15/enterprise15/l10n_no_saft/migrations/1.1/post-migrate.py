from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    # Remove old cron (outdated xsd version)
    env = api.Environment(cr, SUPERUSER_ID, {})
    old_cron_id = env.ref("l10n_no_saft.ir_cron_load_xsd_file").id
    cr.execute(
        f"""DELETE FROM ir_cron
           WHERE id={old_cron_id}
        """
    )

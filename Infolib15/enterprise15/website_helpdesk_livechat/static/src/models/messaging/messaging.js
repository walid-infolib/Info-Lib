/** @odoo-module **/

import { registerFieldPatchModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerFieldPatchModel('mail.messaging', 'website_helpdesk_livechat/static/src/models/messaging/messaging.js', {
    helpdesk_team_available: attr(),
});

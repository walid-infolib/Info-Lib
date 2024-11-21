/** @odoo-module **/

import { registerInstancePatchModel } from '@mail/model/model_core';
import { insert } from '@mail/model/model_field_command';

registerInstancePatchModel('mail.messaging_initializer', 'website_helpdesk_livechat', {

    /**
     * @override
     */
    async _init({ helpdesk_team_available }) {
        this.messaging.update({ helpdesk_team_available });
        await this._super(...arguments);
    },

    /**
     * @override
     */
    _initCommands() {
        this._super();
        if (!this.messaging.helpdesk_team_available) {
            return;
        }
        this.messaging.update({
            commands: insert([
                {
                    help: this.env._t("Create a new helpdesk ticket"),
                    methodName: 'execute_command_helpdesk',
                    name: "helpdesk",
                },
                {
                    help: this.env._t("Search for a helpdesk ticket"),
                    methodName: 'execute_command_helpdesk_search',
                    name: "helpdesk_search",
                },
            ]),
        });
    },
});

/** @odoo-module **/

import '@im_livechat/../tests/helpers/mock_server'; // ensure mail overrides are applied first

import MockServer from 'web.MockServer';

MockServer.include({
    /**
     * @override
     *
     * Adds the helpdesk_team_available key to the return value in order to ensure that the helpdesks command are available inside test environment.
     */
    _mockResUsers_InitMessaging(ids) {
        return {
            ...this._super(...arguments),
            helpdesk_team_available: true,
        }
    },
});

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.marketing_automation.tests.common import MarketingAutomationCommon
from odoo.tests import tagged, users

@tagged('marketing_automation')
class TestMarketingCampaign(MarketingAutomationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.activity = cls._create_activity_mail(
            cls.campaign,
            user=cls.user_marketing_automation,
            act_values={
                'trigger_type': 'begin',
                'interval_number': 0, 'interval_type': 'hours',
            },
        )

    @users('user_marketing_automation')
    def test_duplicate_campaign(self):
        # duplicate campaign
        original_campaign = self.campaign.with_user(self.env.user)
        duplicated_campaign = original_campaign.copy()
        for campaign in original_campaign + duplicated_campaign:
            with self.subTest(campaign=campaign.name):
                campaign.sync_participants()
                with self.mock_mail_gateway(mail_unlink_sent=False):
                    campaign.execute_activities()
                self.assertMarketAutoTraces(
                    [{
                        'status': 'processed',
                        'records': self.test_contacts,
                        'trace_status': 'sent',
                    }], campaign.marketing_activity_ids)

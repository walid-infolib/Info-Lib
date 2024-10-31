from odoo import _, api, models
from odoo.exceptions import ValidationError


def _check_vat_pattern(partner):
    return partner.check_vat_tn(partner.vat)


class ReportWithholdingTaxStructure(models.AbstractModel):
    _name = "report.l10n_tn_withholding_tax.report_withholding_tax_structure"
    _description = "Withholding Tax Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = []
        for account_payment_id in docids:
            account_payment = self.env["account.payment"].browse(account_payment_id)
            if not account_payment:
                continue
            if account_payment.withholding_tax_id:
                if account_payment.payment_type == "outbound":
                    paying_agency = account_payment.company_id.partner_id
                    recipient = account_payment.partner_id
                else:
                    paying_agency = account_payment.partner_id
                    recipient = account_payment.company_id.partner_id
                if _check_vat_pattern(paying_agency) and _check_vat_pattern(recipient):
                    docs.append(self._get_pdf_doc(account_payment_id, data))
            else:
                raise ValidationError(
                    _("Error ! You should specify a withholding tax.")
                )
        return {
            "doc_ids": docids,
            "doc_model": "account.account.payment",
            "docs": docs,
        }

    @api.model
    def _get_pdf_doc(self, account_payment_id, data):
        doc = {}
        withholding_data = []
        account_payment = self.env["account.payment"].browse(account_payment_id)
        if account_payment.payment_type == "outbound":
            paying_agency = account_payment.company_id
            recipient = account_payment.partner_id
        else:
            paying_agency = account_payment.partner_id
            recipient = account_payment.company_id
        data["designation"] = account_payment.withholding_tax_id.designation
        data["subtotal"] = account_payment.amount_net
        data["total"] = account_payment.amount
        data["amount"] = account_payment.withholding_amount
        withholding_data.append(data)
        doc["paying_agency_vat"] = paying_agency.vat
        doc["paying_agency_name"] = paying_agency.name
        doc["paying_agency_address"] = ", ".join(
            filter(
                None,
                [
                    paying_agency.street,
                    paying_agency.street2,
                    paying_agency.city,
                    paying_agency.state_id.name,
                    paying_agency.zip,
                    paying_agency.country_id.name,
                ],
            )
        )
        doc["recipient_vat"] = recipient.vat
        doc["recipient_name"] = recipient.name
        doc["recipient_address"] = ", ".join(
            filter(
                None,
                [
                    recipient.street,
                    recipient.street2,
                    recipient.city,
                    recipient.state_id.name,
                    recipient.zip,
                    recipient.country_id.name,
                ],
            )
        )
        doc["withholding_data"] = withholding_data
        doc["total_price"] = account_payment.amount
        doc["currency_id"] = account_payment.currency_id
        return doc

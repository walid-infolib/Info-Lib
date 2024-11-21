# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import pycompat, float_repr
from odoo.exceptions import ValidationError
from odoo.tools.sql import column_exists, create_column

from datetime import datetime
from collections import namedtuple, defaultdict
import json
import zipfile
import time
import io

BalanceKey = namedtuple('BalanceKey', ['from_code', 'to_code', 'partner_id', 'tax_id'])


class AccountDatevCompany(models.Model):
    _inherit = 'res.company'

    # Adding the fields as company_dependent does not break stable policy
    l10n_de_datev_consultant_number = fields.Char(company_dependent=True)
    l10n_de_datev_client_number = fields.Char(company_dependent=True)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_de_datev_identifier = fields.Integer(
        string='Datev Identifier',
        copy=False,
        tracking=True,
        index=True,
        help="The Datev identifier is a unique identifier for exchange with the government. "
             "If you had previous exports with another identifier, you can put it here. "
             "If it is 0, then it will take the database id + the value in the system parameter "
             "l10n_de.datev_start_count. "
    )

    @api.constrains('l10n_de_datev_identifier')
    def _check_datev_identifier(self):
        self.flush(['l10n_de_datev_identifier'])
        self.env.cr.execute("""
            SELECT 1 FROM res_partner
            WHERE l10n_de_datev_identifier != 0
            GROUP BY l10n_de_datev_identifier
            HAVING COUNT(*) > 1
        """)

        if self.env.cr.dictfetchone():
            raise ValidationError(_('You have already defined a partner with the same Datev identifier. '))


class AccountMoveL10NDe(models.Model):
    _inherit = 'account.move'

    l10n_de_datev_main_account_id = fields.Many2one('account.account', compute='_get_datev_account',
        help='Technical field needed for datev export', store=True)

    def _auto_init(self):
        if column_exists(self.env.cr, "account_move", "l10n_de_datev_main_account_id"):
            return super()._auto_init()

        cr = self.env.cr
        create_column(cr, "account_move", "l10n_de_datev_main_account_id", "int4")
        # If move has an invoice, return invoice's account_id
        cr.execute(
            """
                UPDATE account_move
                   SET l10n_de_datev_main_account_id = r.aid
                  FROM (
                          SELECT l.move_id mid,
                                 FIRST_VALUE(l.account_id) OVER(PARTITION BY l.move_id ORDER BY l.id DESC) aid
                            FROM account_move_line l
                            JOIN account_move m
                              ON m.id = l.move_id
                            JOIN account_account a
                              ON a.id = l.account_id
                            JOIN account_account_type t
                              ON t.id = a.user_type_id
                           WHERE m.move_type in ('out_invoice', 'out_refund', 'in_refund', 'in_invoice', 'out_receipt', 'in_receipt')
                             AND t.type in ('receivable', 'payable')
                       ) r
                WHERE id = r.mid
            """)

        # If move belongs to a bank journal, return the journal's account (debit/credit should normally be the same)
        cr.execute(
            """
            UPDATE account_move
               SET l10n_de_datev_main_account_id = r.aid
              FROM (
                    SELECT m.id mid,
                           j.default_account_id aid
                     FROM account_move m
                     JOIN account_journal j
                       ON m.journal_id = j.id
                    WHERE j.type = 'bank'
                      AND j.default_account_id IS NOT NULL
                   ) r
             WHERE id = r.mid
               AND l10n_de_datev_main_account_id IS NULL
            """)

        # If the move is an automatic exchange rate entry, take the gain/loss account set on the exchange journal
        cr.execute("""
            UPDATE account_move m
               SET l10n_de_datev_main_account_id = r.aid
              FROM (
                    SELECT l.move_id AS mid,
                           l.account_id AS aid
                      FROM account_move_line l
                      JOIN account_move m
                        ON l.move_id = m.id
                      JOIN account_journal j
                        ON m.journal_id = j.id
                      JOIN res_company c
                        ON c.currency_exchange_journal_id = j.id
                     WHERE j.type='general'
                       AND l.account_id = j.default_account_id
                     GROUP BY l.move_id,
                              l.account_id
                    HAVING count(*)=1
                   ) r
             WHERE id = r.mid
               AND l10n_de_datev_main_account_id IS NULL
            """)

        # Look for an account used a single time in the move, that has no originator tax
        query = """
            UPDATE account_move m
               SET l10n_de_datev_main_account_id = r.aid
              FROM (
                    SELECT l.move_id AS mid,
                           min(l.account_id) AS aid
                      FROM account_move_line l
                     WHERE {}
                     GROUP BY move_id
                    HAVING count(*)=1
                   ) r
             WHERE id = r.mid
               AND m.l10n_de_datev_main_account_id IS NULL
            """
        cr.execute(query.format("l.debit > 0"))
        cr.execute(query.format("l.credit > 0"))
        cr.execute(query.format("l.debit > 0 AND l.tax_line_id IS NULL"))
        cr.execute(query.format("l.credit > 0 AND l.tax_line_id IS NULL"))

        return super()._auto_init()

    @api.depends('journal_id', 'line_ids', 'journal_id.default_account_id')
    def _get_datev_account(self):
        for move in self:
            move.l10n_de_datev_main_account_id = value = False
            # If move has an invoice, return invoice's account_id
            if move.is_invoice(include_receipts=True):
                payment_term_lines = move.line_ids.filtered(
                    lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                if payment_term_lines:
                    move.l10n_de_datev_main_account_id = payment_term_lines[0].account_id
                continue
            # If move belongs to a bank journal, return the journal's account (debit/credit should normally be the same)
            if move.journal_id.type == 'bank' and move.journal_id.default_account_id:
                move.l10n_de_datev_main_account_id = move.journal_id.default_account_id
                continue
            # If the move is an automatic exchange rate entry, take the gain/loss account set on the exchange journal
            elif move.journal_id.type == 'general' and move.journal_id == self.env.company.currency_exchange_journal_id:
                lines = move.line_ids.filtered(lambda r: r.account_id == move.journal_id.default_account_id)

                if len(lines) == 1:
                    move.l10n_de_datev_main_account_id = lines.account_id
                    continue

            # Look for an account used a single time in the move, that has no originator tax
            aml_debit = self.env['account.move.line']
            aml_credit = self.env['account.move.line']
            for aml in move.line_ids:
                if aml.debit > 0:
                    aml_debit += aml
                if aml.credit > 0:
                    aml_credit += aml
            if len(aml_debit.account_id) == 1:
                value = aml_debit.account_id
            elif len(aml_credit.account_id) == 1:
                value = aml_credit.account_id
            else:
                aml_debit_wo_tax_accounts = [a.account_id for a in aml_debit if not a.tax_line_id]
                aml_credit_wo_tax_accounts = [a.account_id for a in aml_credit if not a.tax_line_id]
                if len(aml_debit_wo_tax_accounts) == 1:
                    value = aml_debit_wo_tax_accounts[0]
                elif len(aml_credit_wo_tax_accounts) == 1:
                    value = aml_credit_wo_tax_accounts[0]
            move.l10n_de_datev_main_account_id = value


class DatevExportCSV(models.AbstractModel):
    _inherit = 'account.general.ledger'

    def _get_reports_buttons(self, options):
        buttons = super(DatevExportCSV, self)._get_reports_buttons(options)
        buttons += [{'name': _('Datev (zip)'), 'sequence': 3, 'action': 'print_zip', 'file_export_type': _('Datev zip')}]
        return buttons

    # This will be removed in master as export CSV is not needed anymore
    # Can't remove it in version 11 in order to not break the stable policy
    def print_csv(self, options):
        return {
            'type': 'ir_actions_account_report_download',
            'data': {
                'model': self.env.context.get('model'),
                'options': json.dumps(options),
                'output_format': 'csv',
            }
        }

    def print_zip(self, options):
        return {
            'type': 'ir_actions_account_report_download',
            'data': {'model': self.env.context.get('model'),
                     'options': json.dumps(options),
                     'output_format': 'zip',
                     }
        }

    def _get_zip(self, options):
        # Check ir_attachment for method _get_path
        # create a sha and replace 2 first letters by something not hexadecimal
        # Return full_path as 2nd args, use it as name for Zipfile
        # Don't need to unlink as it will be done automatically by bgarbage collector
        # of attachment cron
        # This create a zip file that we store as an ir_attachment. To prevent overwritting
        # an existing ir_attachement, we store it in a folder called ww (all others attachments
        # are inside folders that only has hexadecimal value as name)
        # This is done so that we can send the zip directly to client without putting it
        # in memory. After having created the file, we also have to call _file_delete
        # Otherwise the folder ww won't be garbage collected by the cron
        ir_attachment = self.env['ir.attachment']
        sha = ir_attachment._compute_checksum(str(time.time()).encode('utf-8'))
        fname, full_path = ir_attachment._get_path(False, 'ww' + sha[2:])
        with zipfile.ZipFile(full_path, 'w', False) as zf:
            zf.writestr('EXTF_accounting_entries.csv', self.get_csv(options))
            zf.writestr('EXTF_customer_accounts.csv', self._get_partner_list(options, customer=True))
            zf.writestr('EXTF_vendor_accounts.csv', self._get_partner_list(options, customer=False))
        ir_attachment._file_delete(fname)
        return open(full_path, 'rb')

    def _get_datev_client_number(self):
        consultant_number = self.env.company.l10n_de_datev_consultant_number
        client_number = self.env.company.l10n_de_datev_client_number
        if not consultant_number:
            consultant_number = 99999
        if not client_number:
            client_number = 999
        return [consultant_number, client_number]

    def _get_partner_list(self, options, customer=True):
        date_from = fields.Date.from_string(options.get('date').get('date_from'))
        date_to = fields.Date.from_string(options.get('date').get('date_to'))
        fy = self.env.company.compute_fiscalyear_dates(date_to)

        date_from = datetime.strftime(date_from, '%Y%m%d')
        date_to = datetime.strftime(date_to, '%Y%m%d')
        fy = datetime.strftime(fy.get('date_from'), '%Y%m%d')
        datev_info = self._get_datev_client_number()
        account_length = self._get_account_length()

        output = io.BytesIO()
        writer = pycompat.csv_writer(output, delimiter=';', quotechar='"', quoting=2)
        preheader = ['EXTF', 700, 16, 'Debitoren/Kreditoren', 5, None, None, '', '', '', datev_info[0], datev_info[1], fy, account_length,
            '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
        header = [
            'Konto', 'Name (Adressattyp Unternehmen)', 'Unternehmensgegenstand', 'Name (Adressattyp natürl. Person)',
            'Vorname (Adressattyp natürl. Person)', 'Name (Adressattyp keine Angabe)', 'Adressattyp', 'Kurzbezeichnung',
            'EU-Land', 'EU-UStID', 'Anrede', 'Titel/Akad. Grad', 'Adelstitel', 'Namensvorsatz', 'Adressart', 'Straße',
            'Postfach', 'Postleitzahl', 'Ort', 'Land', 'Versandzusatz', 'Adresszusatz', 'Abweichende Anrede', 'Abw. Zustellbezeichnung 1',
            'Abw. Zustellbezeichnung 2', 'Kennz. Korrespondenzadresse', 'Adresse Gültig von', 'Adresse Gültig bis', 'Telefon',
            'Bemerkung (Telefon)', 'Telefon GL', 'Bemerkung (Telefon GL)', 'E-Mail', 'Bemerkung (E-Mail)', 'Internet',
            'Bemerkung (Internet)', 'Fax', 'Bemerkung (Fax)', 'Sonstige', 'Bemerkung (Sonstige)', 'Bankleitzahl 1',
            'Bankbezeichnung 1', 'Bank-Kontonummer 1', 'Länderkennzeichen 1', 'IBAN-Nr. 1', 'Leerfeld', 'SWIFT-Code 1',
            'Abw. Kontoinhaber 1', 'Kennz. Hauptbankverb. 1', 'Bankverb 1 Gültig von', 'Bankverb 1 Gültig bis', 'Bankleitzahl 2',
            'Bankbezeichnung 2', 'Bank-Kontonummer 2', 'Länderkennzeichen 2', 'IBAN-Nr. 2', 'Leerfeld', 'SWIFT-Code 2',
            'Abw. Kontoinhaber 2', 'Kennz. Hauptbankverb. 2', 'Bankverb 2 Gültig von', 'Bankverb 2 Gültig bis', 'Bankleitzahl 3',
            'Bankbezeichnung 3', 'Bank-Kontonummer 3', 'Länderkennzeichen 3', 'IBAN-Nr. 3', 'Leerfeld', 'SWIFT-Code 3',
            'Abw. Kontoinhaber 3', 'Kennz. Hauptbankverb. 3', 'Bankverb 3 Gültig von', 'Bankverb 3 Gültig bis', 'Bankleitzahl 4',
            'Bankbezeichnung 4', 'Bank-Kontonummer 4', 'Länderkennzeichen 4', 'IBAN-Nr. 4', 'Leerfeld', 'SWIFT-Code 4',
            'Abw. Kontoinhaber 4', 'Kennz. Hauptbankverb. 4', 'Bankverb 4 Gültig von', 'Bankverb 4 Gültig bis', 'Bankleitzahl 5',
            'Bankbezeichnung 5', 'Bank-Kontonummer 5', 'Länderkennzeichen 5', 'IBAN-Nr. 5', 'Leerfeld', 'SWIFT-Code 5',
            'Abw. Kontoinhaber 5', 'Kennz. Hauptbankverb. 5', 'Bankverb 5 Gültig von', 'Bankverb 5 Gültig bis', 'Leerfeld',
            'Briefanrede', 'Grußformel', 'Kunden-/Lief.-Nr.', 'Steuernummer', 'Sprache', 'Ansprechpartner', 'Vertreter',
            'Sachbearbeiter', 'Diverse-Konto', 'Ausgabeziel', 'Währungssteuerung', 'Kreditlimit (Debitor)', 'Zahlungsbedingung',
            'Fälligkeit in Tagen (Debitor)', 'Skonto in Prozent (Debitor)', 'Kreditoren-Ziel 1 Tg.', 'Kreditoren-Skonto 1 %',
            'Kreditoren-Ziel 2 Tg.', 'Kreditoren-Skonto 2 %', 'Kreditoren-Ziel 3 Brutto Tg.', 'Kreditoren-Ziel 4 Tg.',
            'Kreditoren-Skonto 4 %', 'Kreditoren-Ziel 5 Tg.', 'Kreditoren-Skonto 5 %', 'Mahnung', 'Kontoauszug', 'Mahntext 1',
            'Mahntext 2', 'Mahntext 3', 'Kontoauszugstext', 'Mahnlimit Betrag', 'Mahnlimit %', 'Zinsberechnung', 'Mahnzinssatz 1',
            'Mahnzinssatz 2', 'Mahnzinssatz 3', 'Lastschrift', 'Leerfeld', 'Mandantenbank', 'Zahlungsträger', 'Indiv. Feld 1',
            'Indiv. Feld 2', 'Indiv. Feld 3', 'Indiv. Feld 4', 'Indiv. Feld 5', 'Indiv. Feld 6', 'Indiv. Feld 7', 'Indiv. Feld 8',
            'Indiv. Feld 9', 'Indiv. Feld 10', 'Indiv. Feld 11', 'Indiv. Feld 12', 'Indiv. Feld 13', 'Indiv. Feld 14',
            'Indiv. Feld 15', 'Abweichende Anrede (Rechnungsadresse)', 'Adressart (Rechnungsadresse)', 'Straße (Rechnungsadresse)',
            'Postfach (Rechnungsadresse)', 'Postleitzahl (Rechnungsadresse)', 'Ort (Rechnungsadresse)', 'Land (Rechnungsadresse)',
            'Versandzusatz (Rechnungsadresse)', 'Adresszusatz (Rechnungsadresse)', 'Abw. Zustellbezeichnung 1 (Rechnungsadresse)',
            'Abw. Zustellbezeichnung 2 (Rechnungsadresse)', 'Adresse Gültig von (Rechnungsadresse)', 'Adresse Gültig bis (Rechnungsadresse)',
            'Bankleitzahl 6', 'Bankbezeichnung 6', 'Bank-Kontonummer 6', 'Länderkennzeichen 6', 'IBAN-Nr. 6', 'Leerfeld',
            'SWIFT-Code 6', 'Abw. Kontoinhaber 6', 'Kennz. Hauptbankverb. 6', 'Bankverb 6 Gültig von', 'Bankverb 6 Gültig bis',
            'Bankleitzahl 7', 'Bankbezeichnung 7', 'Bank-Kontonummer 7', 'Länderkennzeichen 7', 'IBAN-Nr. 7', 'Leerfeld',
            'SWIFT-Code 7', 'Abw. Kontoinhaber 7', 'Kennz. Hauptbankverb. 7', 'Bankverb 7 Gültig von', 'Bankverb 7 Gültig bis',
            'Bankleitzahl 8', 'Bankbezeichnung 8', 'Bank-Kontonummer 8', 'Länderkennzeichen 8', 'IBAN-Nr. 8', 'Leerfeld',
            'SWIFT-Code 8', 'Abw. Kontoinhaber 8', 'Kennz. Hauptbankverb. 8', 'Bankverb 8 Gültig von', 'Bankverb 8 Gültig bis',
            'Bankleitzahl 9', 'Bankbezeichnung 9', 'Bank-Kontonummer 9', 'Länderkennzeichen 9', 'IBAN-Nr. 9', 'Leerfeld',
            'SWIFT-Code 9', 'Abw. Kontoinhaber 9', 'Kennz. Hauptbankverb. 9', 'Bankverb 9 Gültig von', 'Bankverb 9 Gültig bis',
            'Bankleitzahl 10', 'Bankbezeichnung 10', 'Bank-Kontonummer 10', 'Länderkennzeichen 10', 'IBAN-Nr. 10', 'Leerfeld',
            'SWIFT-Code 10', 'Abw. Kontoinhaber 10', 'Kennz. Hauptbankverb. 10', 'Bankverb 10 Gültig von', 'Bankverb 10 Gültig bis',
            'Nummer Fremdsystem', 'Insolvent', 'SEPA-Mandatsreferenz 1', 'SEPA-Mandatsreferenz 2', 'SEPA-Mandatsreferenz 3',
            'SEPA-Mandatsreferenz 4', 'SEPA-Mandatsreferenz 5', 'SEPA-Mandatsreferenz 6', 'SEPA-Mandatsreferenz 7',
            'SEPA-Mandatsreferenz 8', 'SEPA-Mandatsreferenz 9', 'SEPA-Mandatsreferenz 10', 'Verknüpftes OPOS-Konto',
            'Mahnsperre bis', 'Lastschriftsperre bis', 'Zahlungssperre bis', 'Gebührenberechnung', 'Mahngebühr 1', 'Mahngebühr 2',
            'Mahngebühr 3', 'Pauschalenberechnung', 'Verzugspauschale 1', 'Verzugspauschale 2', 'Verzugspauschale 3',
            'Alternativer Suchname', 'Status', 'Anschrift manuell geändert (Korrespondenzadresse)', 'Anschrift individuell (Korrespondenzadresse)',
            'Anschrift manuell geändert (Rechnungsadresse)', 'Anschrift individuell (Rechnungsadresse)', 'Fristberechnung bei Debitor',
            'Mahnfrist 1', 'Mahnfrist 2', 'Mahnfrist 3', 'Letzte Frist',
        ]

        # if we do _get_lines with some unfolded lines, only those will be returned, but we want all of them
        move_line_ids = self.with_context(self._set_context(options), print_mode=True, aml_only=True)._get_lines({**options, 'unfolded_lines': []})
        lines = [preheader, header]

        self.env['account.move'].flush()

        if len(move_line_ids):
            if customer:
                move_types = ('out_refund', 'out_invoice', 'out_receipt')
            else:
                move_types = ('in_refund', 'in_invoice', 'in_receipt')
            select = """SELECT distinct(aml.partner_id)
                        FROM account_move_line aml
                        LEFT JOIN account_move m
                        ON aml.move_id = m.id
                        WHERE aml.id IN %s
                            AND aml.tax_line_id IS NULL
                            AND aml.debit != aml.credit
                            AND m.move_type IN %s
                            AND aml.account_id != m.l10n_de_datev_main_account_id"""
            self.env.cr.execute(select, (tuple(move_line_ids), move_types))
        partners = self.env['res.partner'].browse([p.get('partner_id') for p in self.env.cr.dictfetchall()])
        for partner in partners:
            if customer:
                code = self._find_partner_account(partner.property_account_receivable_id, partner)
            else:
                code = self._find_partner_account(partner.property_account_payable_id, partner)
            line_value = {
                'code': code,
                'company_name': partner.name if partner.is_company else '',
                'person_name': '' if partner.is_company else partner.name,
                'natural': partner.is_company and '2' or '1',
                'vat': partner.vat or '',
            }
            # Idiotic program needs to have a line with 243 elements ordered in a given fashion as it
            # does not take into account the header and non mandatory fields
            array = ['' for x in range(243)]
            array[0] = line_value.get('code')
            array[1] = line_value.get('company_name')
            array[3] = line_value.get('person_name')
            array[6] = line_value.get('natural')
            array[9] = line_value.get('vat')
            lines.append(array)
        writer.writerows(lines)
        return output.getvalue()

    def _get_account_length(self):
        param_start = self.env['ir.config_parameter'].sudo().get_param('l10n_de.datev_start_count', "100000000")[:9]
        param_start_vendors = self.env['ir.config_parameter'].sudo().get_param('l10n_de.datev_start_count_vendors', "700000000")[:9]

        # The gegenkonto should be 1 length higher than the account length, so we have to substract 1 to the params length
        return max(param_start.isdigit() and len(param_start) or 9, param_start_vendors.isdigit() and len(param_start_vendors) or 9, 5) - 1

    def _find_partner_account(self, account, partner):
        len_param = self._get_account_length() + 1
        if (account.internal_type in ('receivable', 'payable') and partner):
            # Check if we have a property as receivable/payable on the partner
            # We use the property because in datev and in germany, partner can be of 2 types
            # important partner which have a specific account number or a virtual partner
            # Which has only a number. To differentiate between the two, if a partner in Odoo
            # explicitely has a receivable/payable account set, we use that account, otherwise
            # we assume it is not an important partner and his datev virtual id will be the
            # l10n_de_datev_identifier set or the id + the start count parameter.
            account = partner.property_account_receivable_id if account.internal_type == 'receivable' else partner.property_account_payable_id
            fname   = "property_account_receivable_id"       if account.internal_type == "receivable" else "property_account_payable_id"
            prop = self.env['ir.property']._get(fname, "res.partner", partner.id)
            force_datev_id = self.env['ir.config_parameter'].sudo().get_param('l10n_de.force_datev_id', False)
            if not force_datev_id and prop == account:
                return str(account.code).ljust(len_param - 1, '0') if account else ''
            return self._get_account_identifier(account, partner)
        return str(account.code).ljust(len_param - 1, '0') if account else ''

    def _get_account_identifier(self, account, partner):
        len_param = self._get_account_length() + 1
        if account.internal_type == 'receivable':
            param_start = self.env['ir.config_parameter'].sudo().get_param('l10n_de.datev_start_count', "100000000")[:9]
            start_count = param_start.isdigit() and int(param_start) or 100000000
        else:
            param_start_vendors = self.env['ir.config_parameter'].sudo().get_param('l10n_de.datev_start_count_vendors', "700000000")[:9]
            start_count = param_start_vendors.isdigit() and int(param_start_vendors) or 700000000
        start_count = int(str(start_count).ljust(len_param, '0'))
        return partner.l10n_de_datev_identifier or start_count + partner.id

    # Source: http://www.datev.de/dnlexom/client/app/index.html#/document/1036228/D103622800029
    def get_csv(self, options):
        # last 2 element of preheader should be filled by "consultant number" and "client number"
        date_from = fields.Date.from_string(options.get('date').get('date_from'))
        date_to = fields.Date.from_string(options.get('date').get('date_to'))
        fy = self.env.company.compute_fiscalyear_dates(date_to)

        date_from = datetime.strftime(date_from, '%Y%m%d')
        date_to = datetime.strftime(date_to, '%Y%m%d')
        fy = datetime.strftime(fy.get('date_from'), '%Y%m%d')
        datev_info = self._get_datev_client_number()
        account_length = self._get_account_length()

        output = io.BytesIO()
        writer = pycompat.csv_writer(output, delimiter=';', quotechar='"', quoting=2)

        preheader = ['EXTF', 700, 21, 'Buchungsstapel', 13, '', '', '', '', '', datev_info[0], datev_info[1], fy, account_length,
            date_from, date_to, '', '', '', '', 0, 'EUR', '', '', '', '', '', '', '', '', '']
        header = [
            'Umsatz (ohne Soll/Haben-Kz)', 'Soll/Haben-Kennzeichen', 'WKZ Umsatz', 'Kurs', 'Basis-Umsatz', 'WKZ Basis-Umsatz',
            'Konto', 'Gegenkonto (ohne BU-Schlüssel)', 'BU-Schlüssel', 'Belegdatum', 'Belegfeld 1', 'Belegfeld 2', 'Skonto',
            'Buchungstext', 'Postensperre', 'Diverse Adressnummer', 'Geschäftspartnerbank', 'Sachverhalt', 'Zinssperre',
            'Beleglink', 'Beleginfo - Art 1', 'Beleginfo - Inhalt 1', 'Beleginfo - Art 2', 'Beleginfo - Inhalt 2',
            'Beleginfo - Art 3', 'Beleginfo - Inhalt 3', 'Beleginfo - Art 4', 'Beleginfo - Inhalt 4',
            'Beleginfo - Art 5', 'Beleginfo - Inhalt 5', 'Beleginfo - Art 6', 'Beleginfo - Inhalt 6',
            'Beleginfo - Art 7', 'Beleginfo - Inhalt 7', 'Beleginfo - Art 8', 'Beleginfo - Inhalt 8', 'KOST1 - Kostenstelle',
            'KOST2 - Kostenstelle', 'Kost-Menge', 'EU-Land u. UStID (Bestimmung)', 'EU-Steuersatz (Bestimmung)',
            'Abw. Versteuerungsart', 'Sachverhalt L+L', 'Funktionsergänzung L+L', 'BU 49 Hauptfunktionstyp', 'BU 49 Hauptfunktionsnummer',
            'BU 49 Funktionsergänzung', 'Zusatzinformation - Art 1', 'Zusatzinformation- Inhalt 1', 'Zusatzinformation - Art 2',
            'Zusatzinformation- Inhalt 2', 'Zusatzinformation - Art 3', 'Zusatzinformation- Inhalt 3', 'Zusatzinformation - Art 4',
            'Zusatzinformation- Inhalt 4', 'Zusatzinformation - Art 5', 'Zusatzinformation- Inhalt 5', 'Zusatzinformation - Art 6',
            'Zusatzinformation- Inhalt 6', 'Zusatzinformation - Art 7', 'Zusatzinformation- Inhalt 7', 'Zusatzinformation - Art 8',
            'Zusatzinformation- Inhalt 8', 'Zusatzinformation - Art 9', 'Zusatzinformation- Inhalt 9', 'Zusatzinformation - Art 10',
            'Zusatzinformation- Inhalt 10', 'Zusatzinformation - Art 11', 'Zusatzinformation- Inhalt 11', 'Zusatzinformation - Art 12',
            'Zusatzinformation- Inhalt 12', 'Zusatzinformation - Art 13', 'Zusatzinformation- Inhalt 13', 'Zusatzinformation - Art 14',
            'Zusatzinformation- Inhalt 14', 'Zusatzinformation - Art 15', 'Zusatzinformation- Inhalt 15', 'Zusatzinformation - Art 16',
            'Zusatzinformation- Inhalt 16', 'Zusatzinformation - Art 17', 'Zusatzinformation- Inhalt 17', 'Zusatzinformation - Art 18',
            'Zusatzinformation- Inhalt 18', 'Zusatzinformation - Art 19', 'Zusatzinformation- Inhalt 19', 'Zusatzinformation - Art 20',
            'Zusatzinformation- Inhalt 20', 'Stück', 'Gewicht', 'Zahlweise', 'Forderungsart', 'Veranlagungsjahr', 'Zugeordnete Fälligkeit',
            'Skontotyp', 'Auftragsnummer', 'Buchungstyp', 'USt-Schlüssel (Anzahlungen)', 'EU-Land (Anzahlungen)', 'Sachverhalt L+L (Anzahlungen)',
            'EU-Steuersatz (Anzahlungen)', 'Erlöskonto (Anzahlungen)', 'Herkunft-Kz', 'Buchungs GUID', 'KOST-Datum', 'SEPA-Mandatsreferenz',
            'Skontosperre', 'Gesellschaftername', 'Beteiligtennummer', 'Identifikationsnummer', 'Zeichnernummer', 'Postensperre bis',
            'Bezeichnung SoBil-Sachverhalt', 'Kennzeichen SoBil-Buchung', 'Festschreibung', 'Leistungsdatum', 'Datum Zuord. Steuerperiode',
            'Fälligkeit', 'Generalumkehr (GU)', 'Steuersatz', 'Land', 'Abrechnungsreferenz', 'BVV-Position', 'EU-Land u. UStID (Ursprung)',
            'EU-Steuersatz (Ursprung)', 'Abw. Skontokonto',
        ]

        # if we do _get_lines with some unfolded lines, only those will be returned, but we want all of them
        move_line_ids = self.with_context(self._set_context(options), print_mode=True, aml_only=True)._get_lines({**options, 'unfolded_lines': []})
        lines = [preheader, header]

        moves = move_line_ids
        # find all account_move
        if len(move_line_ids):
            self.env.cr.execute("""SELECT distinct(move_id) FROM account_move_line WHERE id IN %s""", (tuple(move_line_ids),))
            move_ids = [l.get('move_id') for l in self.env.cr.dictfetchall()]
            moves = self.env['account.move'].browse(move_ids)
        for m in moves:
            payment_account = 0  # Used for non-reconciled payments

            for aml in m.line_ids:
                if aml.debit == aml.credit:
                    # Ignore debit = credit = 0
                    continue

                # account and counterpart account
                account_code = u'{code}'.format(code=self._find_partner_account(aml.account_id, aml.partner_id))
                to_account_code = str(self._find_partner_account(aml.move_id.l10n_de_datev_main_account_id, aml.partner_id))

                # We don't want to have lines with our outstanding payment/receipt as they don't represent real moves
                # So if payment skip one move line to write, while keeping the account
                # and replace bank account for outstanding payment/receipt for the other line

                if aml.payment_id:
                    if payment_account == 0:
                        payment_account = account_code
                        continue
                    else:
                        to_account_code = payment_account

                # If both account and counteraccount are the same, ignore the line
                if aml.account_id == aml.move_id.l10n_de_datev_main_account_id:
                    continue
                # If line is a tax ignore it as datev requires single line with gross amount and deduct tax itself based
                # on account or on the control key code
                if aml.tax_line_id:
                    continue

                aml_taxes = aml.tax_ids.compute_all(aml.balance, aml.company_id.currency_id, partner=aml.partner_id, handle_price_include=False)
                line_amount = aml_taxes['total_included']

                code_correction = ''
                if aml.tax_ids:
                    codes = set(aml.tax_ids.mapped('l10n_de_datev_code'))
                    if len(codes) == 1:
                        # there should only be one max, else skip code
                        code_correction = codes.pop() or ''

                # reference
                receipt1 = ref = aml.move_id.name
                if aml.move_id.journal_id.type == 'purchase' and aml.move_id.ref:
                    ref = aml.move_id.ref

                # on receivable/payable aml of sales/purchases
                receipt2 = ''
                if to_account_code == account_code and aml.date_maturity:
                    receipt2 = aml.date

                currency = aml.company_id.currency_id

                # Idiotic program needs to have a line with 125 elements ordered in a given fashion as it
                # does not take into account the header and non mandatory fields
                array = ['' for x in range(125)]
                # For DateV, we can't have negative amount on a line, so we need to inverse the amount and inverse the
                # credit/debit symbol.
                array[1] = 'H' if aml.currency_id.compare_amounts(line_amount, 0) < 0 else 'S'
                line_amount = abs(line_amount)
                array[0] = float_repr(line_amount, aml.company_id.currency_id.decimal_places).replace('.', ',')
                array[2] = currency.name
                if aml.currency_id != currency:
                    array[3] = str(aml.currency_id.rate).replace('.', ',')
                    array[4] = float_repr(aml.price_total, aml.currency_id.decimal_places).replace('.', ',')
                    array[5] = aml.currency_id.name
                array[6] = account_code
                array[7] = to_account_code
                array[8] = code_correction
                array[9] = datetime.strftime(aml.move_id.date, '%-d%m')
                array[10] = receipt1[-36:]
                array[11] = receipt2
                array[13] = aml.name or ref
                lines.append(array)

        writer.writerows(lines)
        return output.getvalue()


class report_account_coa(models.AbstractModel):
    _inherit = "account.coa.report"

    def _get_reports_buttons(self, options):
        buttons = super(report_account_coa, self)._get_reports_buttons(options)
        # It doesn't make sense to print the DATEV on anything else than the
        # proper general ledger
        return [b for b in buttons if b.get('action') != 'print_zip']

# -*- coding: utf-8 -*-

import datetime
import logging
import re
from itertools import islice

import requests
from dateutil.relativedelta import relativedelta
from lxml import etree
from pytz import timezone

from odoo import api, fields, models
from odoo.addons.web.controllers.main import xml2json_from_elementtree
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.translate import _

BANXICO_DATE_FORMAT = '%d/%m/%Y'
PROXY_URL = 'https://iap-services.odoo.com'
CBUAE_URL = "https://centralbank.ae/umbraco/Surface/Exchange/GetExchangeRateAllCurrency"
CBEGY_URL = "https://www.cbe.org.eg/en/economic-research/statistics/cbe-exchange-rates"
MAP_CURRENCIES = {
    'US Dollar': 'USD',
    'UAE Dirham': 'AED',
    'Argentine Peso': 'ARS',
    'Australian Dollar': 'AUD',
    'Azerbaijan manat': 'AZN',
    'Bangladesh Taka': 'BDT',
    'Bulgarian lev': 'BGN',
    'Bahrani Dinar': 'BHD',
    'Bahraini Dinar': 'BHD',
    'Brunei Dollar': 'BND',
    'Brazilian Real': 'BRL',
    'Botswana Pula': 'BWP',
    'Belarus Rouble': 'BYN',
    'Canadian Dollar': 'CAD',
    'Swiss Franc': 'CHF',
    'Chilean Peso': 'CLP',
    'Chinese Yuan - Offshore': 'CNH',
    'Chinese Yuan': 'CNY',
    'Colombian Peso': 'COP',
    'Czech Koruna': 'CZK',
    'Danish Krone': 'DKK',
    'Algerian Dinar': 'DZD',
    'Egypt Pound': 'EGP',
    'Ethiopian birr': 'ETB',
    'Euro': 'EUR',
    'GB Pound': 'GBP',
    'Pound Sterling': 'GBP',
    'Hongkong Dollar': 'HKD',
    'Croatian kuna': 'HRK',
    'Hungarian Forint': 'HUF',
    'Indonesia Rupiah': 'IDR',
    'Israeli new shekel': 'ILS',
    'Indian Rupee': 'INR',
    'Iraqi dinar': 'IQD',
    'Iceland Krona': 'ISK',
    'Jordan Dinar': 'JOD',
    'Jordanian Dinar': 'JOD',
    'Japanese Yen': 'JPY',
    'Japanese Yen 100': 'JPY',
    'Kenya Shilling': 'KES',
    'Korean Won': 'KRW',
    'Kuwaiti Dinar': 'KWD',
    'Kazakhstan Tenge': 'KZT',
    'Lebanon Pound': 'LBP',
    'Sri Lanka Rupee': 'LKR',
    'Libyan dinar': 'LYD',
    'Moroccan Dirham': 'MAD',
    'Macedonia Denar': 'MKD',
    'Mauritian rupee': 'MUR',
    'Mexican Peso': 'MXN',
    'Malaysia Ringgit': 'MYR',
    'Nigerian Naira': 'NGN',
    'Norwegian Krone': 'NOK',
    'NewZealand Dollar': 'NZD',
    'Omani Rial': 'OMR',
    'Omani Riyal': 'OMR',
    'Peru Sol': 'PEN',
    'Philippine Piso': 'PHP',
    'Pakistan Rupee': 'PKR',
    'Polish Zloty': 'PLN',
    'Qatari Riyal': 'QAR',
    'Romanian leu': 'RON',
    'Serbian Dinar': 'RSD',
    'Russia Rouble': 'RUB',
    'Saudi Riyal': 'SAR',
    'Singapore Dollar': 'SGD',
    'Swedish Krona': 'SWK',
    'Syrian pound': 'SYP',
    'Thai Baht': 'THB',
    'Turkmen manat': 'TMT',
    'Tunisian Dinar': 'TND',
    'Turkish Lira': 'TRY',
    'Trin Tob Dollar': 'TTD',
    'Taiwan Dollar': 'TWD',
    'Tanzania Shilling': 'TZS',
    'Uganda Shilling': 'UGX',
    'Uzbekistani som': 'UZS',
    'Vietnam Dong': 'VND',
    'Yemen Rial': 'YER',
    'South Africa Rand': 'ZAR',
    'Zambian Kwacha': 'ZMW',
}

CBUAE_CURRENCIES = MAP_CURRENCIES  # renamed constant. Maintained for stable policy

COUNTRY_CURRENCY_PROVIDERS = {
    'AE': 'cbuae',
    'CA': 'boc',
    'CH': 'fta',
    'CL': 'mindicador',
    'EG': 'cbegy',
    'MX': 'banxico',
    'PE': 'bcrp',
    'RO': 'bnr',
    'PL': 'nbp',
    'MY': 'bnm',
    'ID': 'bi',
}

_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = 'res.company'

    currency_interval_unit = fields.Selection([
        ('manually', 'Manually'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')],
        default='manually', string='Interval Unit')
    currency_next_execution_date = fields.Date(string="Next Execution Date")
    currency_provider = fields.Selection([
        ('ecb', 'European Central Bank'),
        ('fta', 'Federal Tax Administration (Switzerland)'),
        ('banxico', 'Mexican Bank'),
        ('boc', 'Bank Of Canada'),
        ('xe_com', 'xe.com'),
        ('bnr', 'National Bank Of Romania'),
        ('mindicador', 'Chilean mindicador.cl'),
        ('bcrp', 'SUNAT (replaces Bank of Peru)'),
        ('cbuae', 'UAE Central Bank'),
        ('cbegy', 'Central Bank of Egypt'),
        ('nbp', 'National Bank of Poland'),
        ('bnb', 'Bulgaria National Bank'),
        ('bnm', 'Bank Negara Malaysia'),
        ('bi', 'Bank Indonesia'),
    ], default='ecb', string='Service Provider')

    @api.model
    def create(self, vals):
        ''' Change the default provider depending on the company data.'''
        if vals.get('country_id') and 'currency_provider' not in vals:
            cc = self.env['res.country'].browse(vals['country_id']).code.upper()
            if cc in COUNTRY_CURRENCY_PROVIDERS:
                vals['currency_provider'] = COUNTRY_CURRENCY_PROVIDERS[cc]
        return super(ResCompany, self).create(vals)

    @api.model
    def set_special_defaults_on_install(self):
        ''' At module installation, set the default provider depending on the company country.'''
        all_companies = self.env['res.company'].search([])
        for company in all_companies:
            company.currency_provider = COUNTRY_CURRENCY_PROVIDERS.get(company.country_id.code, 'ecb')

    def update_currency_rates(self):
        ''' This method is used to update all currencies given by the provider.
        It calls the parse_function of the selected exchange rates provider automatically.

        For this, all those functions must be called _parse_xxx_data, where xxx
        is the technical name of the provider in the selection field. Each of them
        must also be such as:
            - It takes as its only parameter the recordset of the currencies
              we want to get the rates of
            - It returns a dictionary containing currency codes as keys, and
              the corresponding exchange rates as its values. These rates must all
              be based on the same currency, whatever it is. This dictionary must
              also include a rate for the base currencies of the companies we are
              updating rates from, otherwise this will result in an error
              asking the user to choose another provider.

        :return: True if the rates of all the records in self were updated
                 successfully, False if at least one wasn't.
        '''
        rslt = True
        active_currencies = self.env['res.currency'].search([])
        for (currency_provider, companies) in self._group_by_provider().items():
            parse_results = None
            parse_function = getattr(companies, '_parse_' + currency_provider + '_data')
            parse_results = parse_function(active_currencies)

            if parse_results == False:
                # We check == False, and don't use bool conversion, as an empty
                # dict can be returned, if none of the available currencies is supported by the provider
                _logger.warning('Unable to connect to the online exchange rate platform %s. The web service may be temporary down.', currency_provider)
                rslt = False
            else:
                companies._generate_currency_rates(parse_results)

        return rslt

    def _group_by_provider(self):
        """ Returns a dictionnary grouping the companies in self by currency
        rate provider. Companies with no provider defined will be ignored."""
        rslt = {}
        for company in self:
            if not company.currency_provider:
                continue

            if rslt.get(company.currency_provider):
                rslt[company.currency_provider] += company
            else:
                rslt[company.currency_provider] = company
        return rslt

    def _generate_currency_rates(self, parsed_data):
        """ Generate the currency rate entries for each of the companies, using the
        result of a parsing function, given as parameter, to get the rates data.

        This function ensures the currency rates of each company are computed,
        based on parsed_data, so that the currency of this company receives rate=1.
        This is done so because a lot of users find it convenient to have the
        exchange rate of their main currency equal to one in Odoo.
        """
        Currency = self.env['res.currency']
        CurrencyRate = self.env['res.currency.rate']

        for company in self:
            rate_info = parsed_data.get(company.currency_id.name, None)

            if not rate_info:
                msg = _("Your main currency (%s) is not supported by this exchange rate provider. Please choose another one.", company.currency_id.name)
                if self._context.get('suppress_errors'):
                    _logger.warning(msg)
                    continue
                else:
                    raise UserError(msg)

            base_currency_rate = rate_info[0]

            for currency, (rate, date_rate) in parsed_data.items():
                rate_value = rate / base_currency_rate

                currency_object = Currency.search([('name', '=', currency)])
                if currency_object:  # if rate provider base currency is not active, it will be present in parsed_data
                    already_existing_rate = CurrencyRate.search([('currency_id', '=', currency_object.id), ('name', '=', date_rate), ('company_id', '=', company.id)])
                    if already_existing_rate:
                        already_existing_rate.rate = rate_value
                    else:
                        CurrencyRate.create({'currency_id': currency_object.id, 'rate': rate_value, 'name': date_rate, 'company_id': company.id})

    def _parse_fta_data(self, available_currencies):
        ''' Parses the data returned in xml by FTA servers and returns it in a more
        Python-usable form.'''
        request_url = 'https://www.backend-rates.bazg.admin.ch/api/xmldaily?d=yesterday&locale=en'
        try:
            parse_url = requests.request('GET', request_url)
        except:
            return False

        rates_dict = {}
        available_currency_names = available_currencies.mapped('name')
        xml_tree = etree.fromstring(parse_url.content)
        data = xml2json_from_elementtree(xml_tree)
        # valid dates (gueltigkeit) may be comma separated, the first one will do
        date_elem = xml_tree.xpath("//*[local-name() = 'gueltigkeit']")[0]
        date_rate = datetime.datetime.strptime(date_elem.text.split(',')[0], '%d.%m.%Y').date()
        for child_node in data['children']:
            if child_node['tag'] == 'devise':
                currency_code = child_node['attrs']['code'].upper()

                if currency_code in available_currency_names:
                    currency_xml = None
                    rate_xml = None

                    for sub_child in child_node['children']:
                        if sub_child['tag'] == 'waehrung':
                            currency_xml = sub_child['children'][0]
                        elif sub_child['tag'] == 'kurs':
                            rate_xml = sub_child['children'][0]
                        if currency_xml and rate_xml:
                            #avoid iterating for nothing on children
                            break

                    rates_dict[currency_code] = (float(re.search(r'\d+', currency_xml).group()) / float(rate_xml), date_rate)

        if 'CHF' in available_currency_names:
            rates_dict['CHF'] = (1.0, date_rate)

        return rates_dict

    def _parse_ecb_data(self, available_currencies):
        ''' This method is used to update the currencies by using ECB service provider.
            Rates are given against EURO
        '''
        request_url = "http://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
        try:
            parse_url = requests.request('GET', request_url)
        except:
            #connection error, the request wasn't successful
            return False

        xmlstr = etree.fromstring(parse_url.content)
        data = xml2json_from_elementtree(xmlstr)
        node = data['children'][2]['children'][0]
        xmldate = fields.Date.to_date(node['attrs']['time'])
        available_currency_names = available_currencies.mapped('name')
        rslt = {x['attrs']['currency']:(float(x['attrs']['rate']), xmldate) for x in node['children'] if x['attrs']['currency'] in available_currency_names}

        if rslt and 'EUR' in available_currency_names:
            rslt['EUR'] = (1.0, xmldate)

        return rslt

    def _parse_cbuae_data(self, available_currencies):
        ''' This method is used to update the currencies by using UAE Central Bank service provider.
            Exchange rates are expressed as 1 unit of the foreign currency converted into AED
        '''
        # Setting the headers enables retrieval of rates in english
        headers = {
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.centralbank.ae/en/forex-eibor/exchange-rates/'
        }
        try:
            fetched_data = requests.get(CBUAE_URL, headers=headers, timeout=30)
            fetched_data.raise_for_status()
        except Exception:
            return False

        htmlelem = etree.fromstring(fetched_data.content, etree.HTMLParser(encoding='utf-8'))
        rates_entries = htmlelem.xpath("//table/tbody//tr")
        date_elem = htmlelem.xpath("//div[@class='row mb-4']/div/p[last()]")[0]
        date_rate = datetime.datetime.strptime(
            date_elem.text.strip(),
            'Last updated:\r\n\r\n%A %d %B %Y %I:%M:%S %p').date()
        available_currency_names = set(available_currencies.mapped('name'))
        rslt = {}
        for rate_entry in rates_entries:
            # line structure is <td>Currency Description</td><td>rate</td>
            currency_code = MAP_CURRENCIES.get(rate_entry[1].text)
            rate = float(rate_entry[2].text)
            if currency_code in available_currency_names:
                rslt[currency_code] = (1.0/rate, date_rate)

        if 'AED' in available_currency_names:
            rslt['AED'] = (1.0, date_rate)
        return rslt

    def _parse_cbegy_data(self, available_currencies):
        ''' This method is used to update the currencies by using the Central Bank of Egypt service provider.
            Exchange rates are expressed as 1 unit of the foreign currency converted into EGP
        '''
        headers = {
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36',
        }
        try:
            fetched_data = requests.get(CBEGY_URL, headers=headers, timeout=30)
            fetched_data.raise_for_status()
        except Exception:
            return False

        htmlelem = etree.fromstring(fetched_data.content, etree.HTMLParser())
        rates_entries = htmlelem.xpath("//table/tbody/tr")
        date_text = htmlelem.xpath("//p[contains(.,'Rates for Date')]/text()")[1]
        date_rate = datetime.datetime.strptime(date_text.strip(), 'Rates for Date: %d/%m/%Y').date()
        available_currency_names = set(available_currencies.mapped('name'))
        rslt = {}
        for rate_entry in rates_entries:
            currency_code = MAP_CURRENCIES.get(rate_entry[0].text.strip())
            # line structure is <td>Currency Description</td><td>BUY RATE</td><td>SELL RATE</td>
            # we use the average of SELL and BUY rates
            rate = (float(rate_entry[1].text) + float(rate_entry[2].text)) / 2
            if currency_code in available_currency_names:
                rslt[currency_code] = (1.0/rate, date_rate)

        if 'EGP' in available_currency_names:
            rslt['EGP'] = (1.0, date_rate)
        return rslt

    def _parse_boc_data(self, available_currencies):
        """This method is used to update currencies exchange rate by using Bank
           Of Canada daily exchange rate service.
           Exchange rates are expressed as 1 unit of the foreign currency converted into Canadian dollars.
           Keys are in this format: 'FX{CODE}CAD' e.g.: 'FXEURCAD'
        """
        available_currency_names = available_currencies.mapped('name')

        request_url = "http://www.bankofcanada.ca/valet/observations/group/FX_RATES_DAILY/json"
        try:
            response = requests.request('GET', request_url)
        except:
            #connection error, the request wasn't successful
            return False
        if not 'application/json' in response.headers.get('Content-Type', ''):
            return False
        data = response.json()

        # 'observations' key contains rates observations by date
        last_observation_date = sorted([obs['d'] for obs in data['observations']])[-1]
        last_obs = [obs for obs in data['observations'] if obs['d'] == last_observation_date][0]
        last_obs.update({'FXCADCAD': {'v': '1'}})
        date_rate = datetime.datetime.strptime(last_observation_date, "%Y-%m-%d").date()
        rslt = {}
        if 'CAD' in available_currency_names:
            rslt['CAD'] = (1, date_rate)

        for currency_name in available_currency_names:
            currency_obs = last_obs.get('FX{}CAD'.format(currency_name), None)
            if currency_obs is not None:
                rslt[currency_name] = (1.0/float(currency_obs['v']), date_rate)

        return rslt

    def _parse_banxico_data(self, available_currencies):
        """Parse function for Banxico provider.
        * With basement in legal topics in Mexico the rate must be **one** per day and it is equal to the rate known the
        day immediate before the rate is gotten, it means the rate for 02/Feb is the one at 31/jan.
        * The base currency is always MXN but with the inverse 1/rate.
        * The official institution is Banxico.
        * The webservice returns the following currency rates:
            - SF46410 EUR
            - SF60632 CAD
            - SF43718 USD Fixed
            - SF46407 GBP
            - SF46406 JPY
            - SF60653 USD SAT - Officially used from SAT institution
        Source: http://www.banxico.org.mx/portal-mercado-cambiario/
        """
        try:
            payload = {
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {'provider': 'banxico'},
            }
            response = requests.get(
                f'{PROXY_URL}/api/currency_rate/1/get_currency_rates', # Send request to Odoo proxy
                json=payload,
                headers={'content-type': 'application/json'},
                timeout=30,
            ).json()

            if response.get('error'):
                return False
            series = response['result']
        except:
            return False

        available_currency_names = available_currencies.mapped('name')
        rslt = {
            'MXN': (1.0, fields.Date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)),
        }
        foreigns = {
            # position order of the rates from webservices
            'SF46410': 'EUR',
            'SF60632': 'CAD',
            'SF46406': 'JPY',
            'SF46407': 'GBP',
            'SF60653': 'USD',
        }
        for index, currency in foreigns.items():
            if not series.get(index, False):
                continue
            if currency not in available_currency_names:
                continue

            serie = series[index]
            for rate in serie:
                try:
                    foreign_mxn_rate = float(serie[rate])
                except (ValueError, TypeError):
                    continue
                foreign_rate_date = datetime.datetime.strptime(rate, BANXICO_DATE_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)
                rslt[currency] = (1.0/foreign_mxn_rate, foreign_rate_date)
        return rslt

    def _parse_xe_com_data(self, available_currencies):
        """ Parses the currency rates data from xe.com provider.
        As this provider does not have an API, we directly extract what we need
        from HTML.
        """
        url_format = 'http://www.xe.com/currencytables/?from=%(currency_code)s'

        # We generate all the exchange rates relative to the USD. This is purely arbitrary.
        try:
            fetched_data = requests.request('GET', url_format % {'currency_code': 'USD'})
        except:
            return False

        rslt = {}

        available_currency_names = available_currencies.mapped('name')

        htmlelem = etree.fromstring(fetched_data.content, etree.HTMLParser())
        rates_entries = htmlelem.xpath(".//div[@id='table-section']//tbody/tr")
        time_element = htmlelem.xpath(".//div[@id='table-section']/section/p")[0]
        date_rate = datetime.datetime.strptime(time_element.text, '%b %d, %Y, %H:%M UTC').date()

        if 'USD' in available_currency_names:
            rslt['USD'] = (1.0, date_rate)

        for rate_entry in rates_entries:
            # line structure is <th>CODE</th><td>NAME<td><td>UNITS PER CURRENCY</td><td>CURRENCY PER UNIT</td>
            currency_code = ''.join(rate_entry.find('.//th').itertext()).strip()
            if currency_code in available_currency_names:
                rate = float(rate_entry.find("td[2]").text.replace(',', ''))
                rslt[currency_code] = (rate, date_rate)

        return rslt

    def _parse_bnr_data(self, available_currencies):
        ''' This method is used to update the currencies by using
        BNR service provider. Rates are given against RON
        '''
        request_url = "https://www.bnr.ro/nbrfxrates.xml"
        try:
            parse_url = requests.request('GET', request_url)
        except:
            #connection error, the request wasn't successful
            return False

        xmlstr = etree.fromstring(parse_url.content)
        data = xml2json_from_elementtree(xmlstr)
        available_currency_names = available_currencies.mapped('name')
        rate_date = fields.Date.today()
        rslt = {}
        rates_node = data['children'][1]['children'][2]
        if rates_node:
            # Rates are valid for the next day, refer:
            # https://lege5.ro/Gratuit/ha4tomrvge/cursul-de-schimb-valutar-norma-metodologica?dp=ha3tgmzwgu2dk
            rate_date = (datetime.datetime.strptime(
                rates_node['attrs']['date'], DEFAULT_SERVER_DATE_FORMAT
            ) + datetime.timedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
            for x in rates_node['children']:
                if x['attrs']['currency'] in available_currency_names:
                    rslt[x['attrs']['currency']] = (
                        float(x['attrs'].get('multiplier', '1')) / float(x['children'][0]),
                        rate_date
                    )
        if rslt and 'RON' in available_currency_names:
            rslt['RON'] = (1.0, rate_date)
        return rslt

    def _parse_bcrp_data(self, available_currencies):
        """Sunat
        Source: https://www.sunat.gob.pe/descarga/TipoCambio.txt
        * The value of the rate is the "official" rate
        * The base currency is always PEN but with the inverse 1/rate.
        """

        result = {}
        available_currency_names = available_currencies.mapped('name')
        if 'PEN' not in available_currency_names or "USD" not in available_currency_names:
            return result
        result['PEN'] = (1.0, fields.Date.context_today(self.with_context(tz='America/Lima')))
        url_format = "https://www.sunat.gob.pe/a/txt/tipoCambio.txt"
        try:
            res = requests.get(url_format, timeout=10)
            res.raise_for_status()
            line = res.text.splitlines()[0] or ""
        except Exception as e:
            _logger.error(e)
            return result
        sunat_value = line.split("|")
        try:
            rate = float(sunat_value[2])
        except ValueError as e:
            _logger.error(e)
            return result
        rate = 1.0 / rate if rate else 0
        date_rate_str = sunat_value[0]
        date_rate = datetime.datetime.strptime(date_rate_str, '%d/%m/%Y').strftime(DEFAULT_SERVER_DATE_FORMAT)
        result["USD"] = (rate, date_rate)
        return result

    def _parse_mindicador_data(self, available_currencies):
        """Parse function for mindicador.cl provider for Chile
        * Regarding needs of rates in Chile there will be one rate per day, except for UTM index (one per month)
        * The value of the rate is the "official" rate
        * The base currency is always CLP but with the inverse 1/rate.
        * The webservice returns the following currency rates:
            - EUR
            - USD (Dolar Observado)
            - UF (Unidad de Fomento)
            - UTM (Unidad Tributaria Mensual)
        """
        logger = _logger.getChild('mindicador')
        icp = self.env['ir.config_parameter'].sudo()
        server_url = icp.get_param('mindicador_api_url')
        if not server_url:
            server_url = 'https://mindicador.cl/api'
            icp.set_param('mindicador_api_url', server_url)
        foreigns = {
            "USD": "dolar",
            "EUR": "euro",
            "UF": "uf",
            "UTM": "utm",
        }
        available_currency_names = available_currencies.mapped('name')
        logger.debug('mindicador: available currency names: %s', available_currency_names)
        today_date = fields.Date.context_today(self.with_context(tz='America/Santiago'))
        rslt = {
            'CLP': (1.0, fields.Date.to_string(today_date)),
        }
        request_date = today_date.strftime('%d-%m-%Y')
        for index, currency in foreigns.items():
            if index not in available_currency_names:
                logger.debug('Index %s not in available currency name', index)
                continue
            url = server_url + '/%s/%s' % (currency, request_date)
            try:
                res = requests.get(url, timeout=30)
                res.raise_for_status()
            except Exception as e:
                return False
            if 'html' in res.text:
                return False
            data_json = res.json()
            if not data_json['serie']:
                continue
            date = data_json['serie'][0]['fecha'][:10]
            rate = data_json['serie'][0]['valor']
            rslt[index] = (1.0 / rate,  date)
        return rslt

    def _parse_nbp_data(self, available_currencies):
        """ This method is used to update the currencies by using NBP (National Polish Bank) service API.
            Rates are given against PLN.
            Source: https://apps.odoo.com/apps/modules/14.0/trilab_live_currency_nbp/
            Code is mostly from Trilab's app with Trilab's permission.
        """

        # this is url to fetch active (at the moment of fetch) average currency exchange table
        request_url = 'https://api.nbp.pl/api/exchangerates/tables/{}/?format=json'
        requested_currency_codes = available_currencies.mapped('name')
        result = {}

        try:
            # there are 3 tables with currencies:
            #   A - most used ones average,
            #   B - exotic currencies average,
            #   C - common bid/sell
            # we will parse first one and if there are unmatched currencies, proceed with second one

            for table_type in ['A', 'B']:
                if not requested_currency_codes:
                    break

                response = requests.get(request_url.format(table_type), timeout=10)
                response.raise_for_status()
                response_data = response.json()
                for exchange_table in response_data:
                    # there *should not be* be more than one table in response, but let's be on the safe side
                    # and parse this in a loop as response is a list

                    # effective date of this table
                    table_date = datetime.datetime.strptime(
                        exchange_table['effectiveDate'], '%Y-%m-%d'
                    ).date()

                    # for tax purpose, polish companies must use rate of day before transaction
                    # this is achieved by offsetting the rate date by one day
                    table_date += relativedelta(days=1)

                    # add base currency
                    if 'PLN' not in result and 'PLN' in requested_currency_codes:
                        result['PLN'] = (1.0, table_date)

                    for rec in exchange_table['rates']:
                        if rec['code'] in requested_currency_codes:
                            result[rec['code']] = (1.0 / rec['mid'], table_date)
                            requested_currency_codes.remove(rec['code'])

        except (requests.RequestException, ValueError):
            # connection error, the request wasn't successful or date was not parsed
            return False

        return result

    def _parse_bnb_data(self, available_currencies):
        """ This method is used to update the currencies by using BNB (Bulgaria National Bank) service API.
            Rates are given against BGN in an XML file.
            Source: https://www.bnb.bg/AboutUs/AUFAQ/Contr_Exchange_Rates_FAQ?toLang=_EN

            If a currency has no rate, it will be skipped.
        """
        request_url = "https://www.bnb.bg/Statistics/StExternalSector/StExchangeRates/StERForeignCurrencies/index.htm?download=xml&search=&lang=EN"

        try:
            response = requests.get(request_url, timeout=10)
            response.raise_for_status()
            rowset = etree.fromstring(response.content)
        except (requests.RequestException, etree.ParseError):
            # connection error, the request wasn't successful or the content could not be parsed
            return False

        available_currency_names = available_currencies.mapped('name')
        result = {}

        # Skip the first ROW node that does not contain currency information
        for row in islice(rowset.iterfind('.//ROW'), 1, None):
            code = row.findtext('CODE')
            rate = row.findtext('REVERSERATE')
            curr_date = datetime.datetime.strptime(row.findtext('CURR_DATE'), '%d.%m.%Y').date()

            if code in available_currency_names and rate:
                result[code] = (float(rate), curr_date)

        if result and 'BGN' in available_currency_names:
            result['BGN'] = (1.0, curr_date)
        return result

    @api.model
    def _parse_bnm_data(self, available_currencies):
        """ This method is used to update the currencies by using BNM (Bank Negara Malaysia) service API.
            Rates are given against MYR as a JSON.
            Source: https://apikijangportal.bnm.gov.my/openapi

            If a currency has no rate, it will be skipped.
        """
        request_url = "https://api.bnm.gov.my/public/exchange-rate"
        request_headers = {
            'accept': 'application/vnd.BNM.API.v1+json',
        }

        try:
            response = requests.get(request_url, headers=request_headers, timeout=10)
            response.raise_for_status()
            result = response.json()
        except (requests.RequestException, ValueError):
            # connection error, the request wasn't successful or the content could not be parsed
            return False
        data = result.get('data')
        if not data:
            return False

        available_currency_names = available_currencies.mapped('name')
        result = {}

        date = datetime.datetime.now()
        for currency in data:
            currency_code = currency['currency_code']
            if currency_code in available_currency_names:
                date = datetime.datetime.strptime(currency['rate']['date'], '%Y-%m-%d').date()
                rate = (1 / currency['rate']['middle_rate']) * currency['unit']
                result[currency_code] = (float(rate), date)

        if result and 'MYR' not in result:
            result['MYR'] = (1.0, date)

        return result

    @api.model
    def _parse_bi_data(self, available_currencies):
        """
        This method is used to update the currencies by using BI (Bank Indonesia) service API.
        Rates are given against IDR as a XML.
        Source: https://www.bi.go.id/biwebservice/wskursbi.asmx

        If a currency has no rate, it will be skipped.
        """
        request_url = "https://www.bi.go.id/biwebservice/wskursbi.asmx/getSubKursLokal4"

        def _fetched_bi_currency_tables(start_date):
            try:
                response = requests.get(request_url, params={
                    'startdate': start_date,
                }, timeout=10)
                response.raise_for_status()
            except requests.RequestException:
                # connection error or the request wasn't successful
                return []

            try:
                xml_tree = etree.fromstring(response.content)
            except etree.XMLSyntaxError:
                # the content could not be parsed
                return []

            return xml_tree.xpath("//Table")

        # The rates are updated once a day, at 8am. It was asked to try and get today's rate when possible.
        # To avoid too many api calls, we will first check the current time. If it is > 8am, we will try to get
        # today's rate. If it fails, we will fall back on yesterday's.
        # This is to avoid issues where the cron would run before 8am every day and never find today's rates.
        currency_tables = []
        current_datetime = datetime.datetime.now(timezone('Asia/Jakarta'))
        request_date = current_datetime.date()

        if current_datetime.hour >= 8:
            currency_tables = _fetched_bi_currency_tables(request_date.isoformat())

        # If we couldn't find the current day's data (too early, ...) we fall back to yesterday's
        if not currency_tables:
            request_date = (current_datetime - relativedelta(days=1)).date()
            currency_tables = _fetched_bi_currency_tables(request_date.isoformat())

        result = {}
        available_currency_names = available_currencies.mapped('name')
        for table in currency_tables:
            currency_code = table.xpath("normalize-space(.//mts_subkurslokal)")
            if currency_code in available_currency_names:
                selling_rate = table.xpath("number(.//jual_subkurslokal)")
                buying_rate = table.xpath("number(.//beli_subkurslokal)")
                middle_rate = (selling_rate + buying_rate) / 2

                unit = table.xpath("number(.//nil_subkurslokal)")

                rate = (1 / middle_rate) * unit
                result[currency_code] = (rate, request_date)

        # We will still add IDR even if there is no result, as it could happen during public holidays.
        # It will work, but won't update any rates.
        if 'IDR' not in result:
            result['IDR'] = (1.0, request_date)

        return result

    @api.model
    def run_update_currency(self):
        """ This method is called from a cron job to update currency rates.
        """
        records = self.search([('currency_next_execution_date', '<=', fields.Date.today())])
        if records:
            to_update = self.env['res.company']
            for record in records:
                if record.currency_interval_unit == 'daily':
                    next_update = relativedelta(days=+1)
                elif record.currency_interval_unit == 'weekly':
                    next_update = relativedelta(weeks=+1)
                elif record.currency_interval_unit == 'monthly':
                    next_update = relativedelta(months=+1)
                else:
                    record.currency_next_execution_date = False
                    continue
                record.currency_next_execution_date = datetime.date.today() + next_update
                to_update += record
            to_update.with_context(suppress_errors=True).update_currency_rates()


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    currency_interval_unit = fields.Selection(related="company_id.currency_interval_unit", readonly=False)
    currency_provider = fields.Selection(related="company_id.currency_provider", readonly=False)
    currency_next_execution_date = fields.Date(related="company_id.currency_next_execution_date", readonly=False)

    @api.onchange('currency_interval_unit')
    def onchange_currency_interval_unit(self):
        #as the onchange is called upon each opening of the settings, we avoid overwriting
        #the next execution date if it has been already set
        if self.company_id.currency_next_execution_date:
            return
        if self.currency_interval_unit == 'daily':
            next_update = relativedelta(days=+1)
        elif self.currency_interval_unit == 'weekly':
            next_update = relativedelta(weeks=+1)
        elif self.currency_interval_unit == 'monthly':
            next_update = relativedelta(months=+1)
        else:
            self.currency_next_execution_date = False
            return
        self.currency_next_execution_date = datetime.date.today() + next_update

    def update_currency_rates_manually(self):
        self.ensure_one()

        if not (self.company_id.update_currency_rates()):
            raise UserError(_('Unable to connect to the online exchange rate platform. The web service may be temporary down. Please try again in a moment.'))

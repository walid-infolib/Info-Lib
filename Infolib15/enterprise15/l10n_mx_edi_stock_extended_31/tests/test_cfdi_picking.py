from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged
from .common import TestMXDeliveryGuideCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCFDIPickingXml(TestMXDeliveryGuideCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.partner_id.city_id = cls.env.ref('l10n_mx_edi.res_city_mx_chh_032').id

        cls.partner_b.write({
            'street': 'Nevada Street',
            'city': 'Carson City',
            'country_id': cls.env.ref('base.us').id,
            'state_id': cls.env.ref('base.state_us_23').id,
            'zip': 39301,
            'vat': '123456789',
        })

    @freeze_time('2017-01-01')
    def test_delivery_guide_30_outgoing(self):
        picking = self.create_picking()
        picking.l10n_mx_edi_gross_vehicle_weight = 2.0
        cfdi = picking._l10n_mx_edi_create_delivery_guide()

        expected_cfdi = """
            <cfdi:Comprobante
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
                xmlns:cartaporte31="http://www.sat.gob.mx/CartaPorte31"
                Moneda="XXX"
                Serie="NWHOUT"
                SubTotal="0"
                TipoDeComprobante="T"
                Total="0"
                Version="4.0"
                Exportacion="01"
                xsi:schemaLocation="http://www.sat.gob.mx/cfd/4 http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd http://www.sat.gob.mx/CartaPorte31 http://www.sat.gob.mx/sitio_internet/cfd/CartaPorte/CartaPorte31.xsd http://www.sat.gob.mx/sitio_internet/cfd/CartaPorte31/CartaPorte31.xsd"
                Fecha="___ignore___"
                Folio="___ignore___"
                LugarExpedicion="20928">
                <cfdi:Emisor Nombre="ESCUELA KEMPER URGATE" RegimenFiscal="601" Rfc="EKU9003173C9"/>
                <cfdi:Receptor UsoCFDI="S01" Nombre="ESCUELA KEMPER URGATE" Rfc="EKU9003173C9" DomicilioFiscalReceptor="20928" RegimenFiscalReceptor="601"/>
                <cfdi:Conceptos>
                    <cfdi:Concepto Importe="0.00" ValorUnitario="0.00" ObjetoImp="01" NoIdentificacion="01" Cantidad="10.000000" ClaveProdServ="56101500" ClaveUnidad="H87" Descripcion="Product A" Unidad="Units"/>
                </cfdi:Conceptos>
                <cfdi:Complemento>
                    <cartaporte31:CartaPorte Version="3.1" TranspInternac="No" TotalDistRec="120" IdCCP="___ignore___">
                        <cartaporte31:Ubicaciones>
                            <cartaporte31:Ubicacion TipoUbicacion="Origen" IDUbicacion="___ignore___" FechaHoraSalidaLlegada="___ignore___" RFCRemitenteDestinatario="EKU9003173C9">
                                <cartaporte31:Domicilio Calle="Campobasso Norte 3206/9000" CodigoPostal="20928" Estado="AGU" Pais="MEX" Municipio="032"/>
                            </cartaporte31:Ubicacion>
                            <cartaporte31:Ubicacion TipoUbicacion="Destino" IDUbicacion="___ignore___" DistanciaRecorrida="120" FechaHoraSalidaLlegada="___ignore___" RFCRemitenteDestinatario="ICV060329BY0">
                                <cartaporte31:Domicilio Calle="Street Calle" CodigoPostal="33826" Estado="CHH" Pais="MEX" Municipio="032"/>
                            </cartaporte31:Ubicacion>
                        </cartaporte31:Ubicaciones>
                        <cartaporte31:Mercancias NumTotalMercancias="1" PesoBrutoTotal="10.000" UnidadPeso="KGM">
                            <cartaporte31:Mercancia BienesTransp="56101500" Cantidad="10.000000" ClaveUnidad="H87" Descripcion="Product A" PesoEnKg="10.000">
                                <cartaporte31:CantidadTransporta Cantidad="10.000000" IDOrigen="___ignore___" IDDestino="DE000005"/>
                            </cartaporte31:Mercancia>
                            <cartaporte31:Autotransporte NumPermisoSCT="DEMOPERMIT" PermSCT="TPAF10">
                                <cartaporte31:IdentificacionVehicular AnioModeloVM="2020" ConfigVehicular="T3S1" PlacaVM="ABC123" PesoBrutoVehicular="2.0"/>
                                <cartaporte31:Seguros AseguraRespCivil="DEMO INSURER" PolizaRespCivil="DEMO POLICY"/>
                                <cartaporte31:Remolques>
                                    <cartaporte31:Remolque SubTipoRem="CTR003" Placa="trail1"/>
                                </cartaporte31:Remolques>
                            </cartaporte31:Autotransporte>
                        </cartaporte31:Mercancias>
                        <cartaporte31:FiguraTransporte>
                            <cartaporte31:TiposFigura TipoFigura="01" RFCFigura="VAAM130719H60" NumLicencia="a234567890" NombreFigura="Amigo Pedro">
                            </cartaporte31:TiposFigura>
                            <cartaporte31:TiposFigura TipoFigura="02" RFCFigura="EKU9003173C9" NombreFigura="ESCUELA KEMPER URGATE">
                                <cartaporte31:PartesTransporte ParteTransporte="PT05"/>
                            </cartaporte31:TiposFigura>
                        </cartaporte31:FiguraTransporte>
                    </cartaporte31:CartaPorte>
                </cfdi:Complemento>
            </cfdi:Comprobante>
        """
        current_etree = self.get_xml_tree_from_string(cfdi)
        expected_etree = self.get_xml_tree_from_string(expected_cfdi)
        self.assertXmlTreeEqual(current_etree, expected_etree)

    @freeze_time('2017-01-01')
    def test_delivery_guide_30_incoming(self):
        picking = self.create_picking(picking_type_id=self.new_wh.in_type_id.id)
        picking.l10n_mx_edi_gross_vehicle_weight = 2.0
        cfdi = picking._l10n_mx_edi_create_delivery_guide()

        expected_cfdi = """
            <cfdi:Comprobante
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
                xmlns:cartaporte31="http://www.sat.gob.mx/CartaPorte31"
                Moneda="XXX"
                Serie="NWHIN"
                SubTotal="0"
                TipoDeComprobante="T"
                Total="0"
                Version="4.0"
                Exportacion="01"
                xsi:schemaLocation="http://www.sat.gob.mx/cfd/4 http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd http://www.sat.gob.mx/CartaPorte31 http://www.sat.gob.mx/sitio_internet/cfd/CartaPorte/CartaPorte31.xsd http://www.sat.gob.mx/sitio_internet/cfd/CartaPorte31/CartaPorte31.xsd"
                Fecha="___ignore___"
                Folio="___ignore___"
                LugarExpedicion="20928">
                <cfdi:Emisor Nombre="ESCUELA KEMPER URGATE" RegimenFiscal="601" Rfc="EKU9003173C9"/>
                <cfdi:Receptor UsoCFDI="S01" Nombre="ESCUELA KEMPER URGATE" Rfc="EKU9003173C9" DomicilioFiscalReceptor="20928" RegimenFiscalReceptor="601"/>
                <cfdi:Conceptos>
                    <cfdi:Concepto Importe="0.00" ValorUnitario="0.00" ObjetoImp="01" NoIdentificacion="01" Cantidad="10.000000" ClaveProdServ="56101500" ClaveUnidad="H87" Descripcion="Product A" Unidad="Units">
                    </cfdi:Concepto>
                </cfdi:Conceptos>
                <cfdi:Complemento>
                    <cartaporte31:CartaPorte Version="3.1" TranspInternac="No" TotalDistRec="120" IdCCP="___ignore___">
                        <cartaporte31:Ubicaciones>
                            <cartaporte31:Ubicacion TipoUbicacion="Origen" IDUbicacion="___ignore___" FechaHoraSalidaLlegada="2016-12-31T18:00:00" RFCRemitenteDestinatario="ICV060329BY0">
                                <cartaporte31:Domicilio Calle="Street Calle" CodigoPostal="33826" Estado="CHH" Pais="MEX" Municipio="032"/>
                            </cartaporte31:Ubicacion>
                            <cartaporte31:Ubicacion TipoUbicacion="Destino" IDUbicacion="___ignore___" DistanciaRecorrida="120" FechaHoraSalidaLlegada="2016-12-31T18:00:00" RFCRemitenteDestinatario="EKU9003173C9">
                                <cartaporte31:Domicilio Calle="Campobasso Norte 3206/9000" CodigoPostal="20928" Estado="AGU" Pais="MEX" Municipio="032"/>
                            </cartaporte31:Ubicacion>
                        </cartaporte31:Ubicaciones>
                        <cartaporte31:Mercancias NumTotalMercancias="1" PesoBrutoTotal="10.000" UnidadPeso="KGM">
                            <cartaporte31:Mercancia BienesTransp="56101500" Cantidad="10.000000" ClaveUnidad="H87" Descripcion="Product A" PesoEnKg="10.000">
                                <cartaporte31:CantidadTransporta Cantidad="10.000000" IDOrigen="___ignore___" IDDestino="___ignore___"/>
                            </cartaporte31:Mercancia>
                            <cartaporte31:Autotransporte NumPermisoSCT="DEMOPERMIT" PermSCT="TPAF10">
                                <cartaporte31:IdentificacionVehicular AnioModeloVM="2020" ConfigVehicular="T3S1" PlacaVM="ABC123" PesoBrutoVehicular="2.0"/>
                                <cartaporte31:Seguros AseguraRespCivil="DEMO INSURER" PolizaRespCivil="DEMO POLICY"/>
                                <cartaporte31:Remolques>
                                    <cartaporte31:Remolque SubTipoRem="CTR003" Placa="trail1"/>
                                </cartaporte31:Remolques>
                            </cartaporte31:Autotransporte>
                        </cartaporte31:Mercancias>
                        <cartaporte31:FiguraTransporte>
                            <cartaporte31:TiposFigura TipoFigura="01" RFCFigura="VAAM130719H60" NumLicencia="a234567890" NombreFigura="Amigo Pedro">
                            </cartaporte31:TiposFigura>
                            <cartaporte31:TiposFigura TipoFigura="02" RFCFigura="EKU9003173C9" NombreFigura="ESCUELA KEMPER URGATE">
                                <cartaporte31:PartesTransporte ParteTransporte="PT05"/>
                            </cartaporte31:TiposFigura>
                        </cartaporte31:FiguraTransporte>
                    </cartaporte31:CartaPorte>
                </cfdi:Complemento>
            </cfdi:Comprobante>
        """
        current_etree = self.get_xml_tree_from_string(cfdi)
        expected_etree = self.get_xml_tree_from_string(expected_cfdi)
        self.assertXmlTreeEqual(current_etree, expected_etree)

    @freeze_time('2017-01-01')
    def test_delivery_guide_comex_30_outgoing(self):
        self.productA.l10n_mx_edi_material_type = '05'
        self.productA.l10n_mx_edi_material_description = 'Test material description'

        picking = self.create_picking(partner_id=self.partner_b.id)

        picking.l10n_mx_edi_gross_vehicle_weight = 2.0
        picking.l10n_mx_edi_customs_document_type_id = self.env.ref('l10n_mx_edi_stock_extended_30.l10n_mx_edi_customs_document_type_02').id
        picking.l10n_mx_edi_customs_doc_identification = '0123456789'
        picking.l10n_mx_edi_customs_regime_ids = [Command.set([
            self.env.ref('l10n_mx_edi_stock_extended_30.l10n_mx_edi_customs_regime_imd').id,
            self.env.ref('l10n_mx_edi_stock_extended_30.l10n_mx_edi_customs_regime_exd').id,
        ])]

        expected_cfdi = """
            <cfdi:Comprobante
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
                xmlns:cartaporte31="http://www.sat.gob.mx/CartaPorte31"
                Moneda="XXX"
                Serie="NWHOUT"
                SubTotal="0"
                TipoDeComprobante="T"
                Total="0"
                Version="4.0"
                Exportacion="01"
                xsi:schemaLocation="http://www.sat.gob.mx/cfd/4 http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd http://www.sat.gob.mx/CartaPorte31 http://www.sat.gob.mx/sitio_internet/cfd/CartaPorte/CartaPorte31.xsd http://www.sat.gob.mx/sitio_internet/cfd/CartaPorte31/CartaPorte31.xsd"
                Fecha="___ignore___"
                Folio="___ignore___"
                LugarExpedicion="20928">
                <cfdi:Emisor Nombre="ESCUELA KEMPER URGATE" RegimenFiscal="601" Rfc="EKU9003173C9"/>
                <cfdi:Receptor UsoCFDI="S01" Nombre="ESCUELA KEMPER URGATE" Rfc="EKU9003173C9" DomicilioFiscalReceptor="20928" RegimenFiscalReceptor="601"/>
                <cfdi:Conceptos>
                    <cfdi:Concepto Importe="0.00" ValorUnitario="0.00" ObjetoImp="01" NoIdentificacion="01" Cantidad="10.000000" ClaveProdServ="56101500" ClaveUnidad="H87" Descripcion="Product A" Unidad="Units">
                    </cfdi:Concepto>
                </cfdi:Conceptos>
                <cfdi:Complemento>
                    <cartaporte31:CartaPorte Version="3.1" TranspInternac="Sí" TotalDistRec="120" EntradaSalidaMerc="Salida" ViaEntradaSalida="01" PaisOrigenDestino="USA" IdCCP="___ignore___">
                        <cartaporte31:RegimenesAduaneros>
                            <cartaporte31:RegimenAduaneroCCP RegimenAduanero="IMD"/>
                            <cartaporte31:RegimenAduaneroCCP RegimenAduanero="EXD"/>
                        </cartaporte31:RegimenesAduaneros>
                        <cartaporte31:Ubicaciones>
                            <cartaporte31:Ubicacion TipoUbicacion="Origen" IDUbicacion="___ignore___" FechaHoraSalidaLlegada="___ignore___" RFCRemitenteDestinatario="EKU9003173C9">
                                <cartaporte31:Domicilio Calle="Campobasso Norte 3206/9000" CodigoPostal="20928" Estado="AGU" Pais="MEX" Municipio="032"/>
                            </cartaporte31:Ubicacion>
                            <cartaporte31:Ubicacion TipoUbicacion="Destino" IDUbicacion="___ignore___" DistanciaRecorrida="120" FechaHoraSalidaLlegada="___ignore___" RFCRemitenteDestinatario="XEXX010101000" NumRegIdTrib="123456789" ResidenciaFiscal="USA">
                                <cartaporte31:Domicilio Calle="Nevada Street" CodigoPostal="39301" Estado="NV" Pais="USA" Municipio="Carson City"/>
                            </cartaporte31:Ubicacion>
                        </cartaporte31:Ubicaciones>
                        <cartaporte31:Mercancias NumTotalMercancias="1" PesoBrutoTotal="10.000" UnidadPeso="KGM">
                            <cartaporte31:Mercancia BienesTransp="56101500" Cantidad="10.000000" ClaveUnidad="H87" Descripcion="Product A" PesoEnKg="10.000" TipoMateria="05" DescripcionMateria="Test material description">
                                <cartaporte31:DocumentacionAduanera xmlns:cartaporte31="http://www.sat.gob.mx/CartaPorte31" TipoDocumento="02" IdentDocAduanero="0123456789"/>
                                <cartaporte31:CantidadTransporta Cantidad="10.000000" IDOrigen="___ignore___" IDDestino="DE000005"/>
                            </cartaporte31:Mercancia>
                            <cartaporte31:Autotransporte NumPermisoSCT="DEMOPERMIT" PermSCT="TPAF10">
                                <cartaporte31:IdentificacionVehicular AnioModeloVM="2020" ConfigVehicular="T3S1" PlacaVM="ABC123" PesoBrutoVehicular="2.0"/>
                                <cartaporte31:Seguros AseguraRespCivil="DEMO INSURER" PolizaRespCivil="DEMO POLICY"/>
                                <cartaporte31:Remolques>
                                    <cartaporte31:Remolque SubTipoRem="CTR003" Placa="trail1"/>
                                </cartaporte31:Remolques>
                            </cartaporte31:Autotransporte>
                        </cartaporte31:Mercancias>
                        <cartaporte31:FiguraTransporte>
                            <cartaporte31:TiposFigura TipoFigura="01" RFCFigura="VAAM130719H60" NumLicencia="a234567890" NombreFigura="Amigo Pedro">
                            </cartaporte31:TiposFigura>
                            <cartaporte31:TiposFigura TipoFigura="02" RFCFigura="EKU9003173C9" NombreFigura="ESCUELA KEMPER URGATE">
                                <cartaporte31:PartesTransporte ParteTransporte="PT05"/>
                            </cartaporte31:TiposFigura>
                        </cartaporte31:FiguraTransporte>
                    </cartaporte31:CartaPorte>
                </cfdi:Complemento>
            </cfdi:Comprobante>
        """

        current_etree = self.get_xml_tree_from_string(picking._l10n_mx_edi_create_delivery_guide())
        expected_etree = self.get_xml_tree_from_string(expected_cfdi)
        self.assertXmlTreeEqual(current_etree, expected_etree)

    @freeze_time('2017-01-01')
    def test_delivery_guide_comex_30_incoming(self):
        self.productA.l10n_mx_edi_material_type = '01'

        picking = self.create_picking(partner_id=self.partner_b.id, picking_type_id=self.new_wh.in_type_id.id)

        picking.l10n_mx_edi_gross_vehicle_weight = 2.0
        picking.l10n_mx_edi_customs_document_type_id = self.env.ref('l10n_mx_edi_stock_extended_30.l10n_mx_edi_customs_document_type_01').id
        picking.l10n_mx_edi_importer_id = self.partner_a.id
        picking.l10n_mx_edi_customs_regime_ids = [Command.set([
            self.env.ref('l10n_mx_edi_stock_extended_30.l10n_mx_edi_customs_regime_imd').id,
            self.env.ref('l10n_mx_edi_stock_extended_30.l10n_mx_edi_customs_regime_exd').id,
        ])]

        expected_cfdi = """
            <cfdi:Comprobante
                xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
                xmlns:cartaporte31="http://www.sat.gob.mx/CartaPorte31"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                Moneda="XXX"
                Serie="NWHIN"
                SubTotal="0"
                TipoDeComprobante="T"
                Total="0"
                Version="4.0"
                Exportacion="01"
                xsi:schemaLocation="http://www.sat.gob.mx/cfd/4 http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd http://www.sat.gob.mx/CartaPorte31 http://www.sat.gob.mx/sitio_internet/cfd/CartaPorte/CartaPorte31.xsd http://www.sat.gob.mx/sitio_internet/cfd/CartaPorte31/CartaPorte31.xsd"
                Fecha="___ignore___"
                Folio="___ignore___"
                LugarExpedicion="20928">
                <cfdi:Emisor Nombre="ESCUELA KEMPER URGATE" RegimenFiscal="601" Rfc="EKU9003173C9"/>
                <cfdi:Receptor UsoCFDI="S01" Nombre="ESCUELA KEMPER URGATE" Rfc="EKU9003173C9" DomicilioFiscalReceptor="20928" RegimenFiscalReceptor="601"/>
                <cfdi:Conceptos>
                    <cfdi:Concepto Importe="0.00" ValorUnitario="0.00" ObjetoImp="01" NoIdentificacion="01" Cantidad="10.000000" ClaveProdServ="56101500" ClaveUnidad="H87" Descripcion="Product A" Unidad="Units">
                    </cfdi:Concepto>
                </cfdi:Conceptos>
                <cfdi:Complemento>
                    <cartaporte31:CartaPorte Version="3.1" TranspInternac="Sí" TotalDistRec="120" EntradaSalidaMerc="Entrada" ViaEntradaSalida="01" PaisOrigenDestino="USA" IdCCP="___ignore___">
                        <cartaporte31:RegimenesAduaneros>
                            <cartaporte31:RegimenAduaneroCCP RegimenAduanero="IMD"/>
                            <cartaporte31:RegimenAduaneroCCP RegimenAduanero="EXD"/>
                        </cartaporte31:RegimenesAduaneros>
                        <cartaporte31:Ubicaciones>
                            <cartaporte31:Ubicacion TipoUbicacion="Origen" IDUbicacion="___ignore___" FechaHoraSalidaLlegada="___ignore___" RFCRemitenteDestinatario="XEXX010101000" NumRegIdTrib="123456789" ResidenciaFiscal="USA">
                                <cartaporte31:Domicilio Calle="Nevada Street" CodigoPostal="39301" Estado="NV" Pais="USA" Municipio="Carson City"/>
                            </cartaporte31:Ubicacion>
                            <cartaporte31:Ubicacion TipoUbicacion="Destino" IDUbicacion="___ignore___" DistanciaRecorrida="120" FechaHoraSalidaLlegada="___ignore___" RFCRemitenteDestinatario="EKU9003173C9">
                                <cartaporte31:Domicilio Calle="Campobasso Norte 3206/9000" CodigoPostal="20928" Estado="AGU" Pais="MEX" Municipio="032"/>
                            </cartaporte31:Ubicacion>
                        </cartaporte31:Ubicaciones>
                        <cartaporte31:Mercancias NumTotalMercancias="1" PesoBrutoTotal="10.000" UnidadPeso="KGM">
                            <cartaporte31:Mercancia BienesTransp="56101500" Cantidad="10.000000" ClaveUnidad="H87" Descripcion="Product A" PesoEnKg="10.000" TipoMateria="01">
                                <cartaporte31:DocumentacionAduanera xmlns:cartaporte31="http://www.sat.gob.mx/CartaPorte31" TipoDocumento="01" RFCImpo="ICV060329BY0"/>
                                <cartaporte31:CantidadTransporta Cantidad="10.000000" IDOrigen="___ignore___" IDDestino="___ignore___"/>
                            </cartaporte31:Mercancia>
                            <cartaporte31:Autotransporte NumPermisoSCT="DEMOPERMIT" PermSCT="TPAF10">
                                <cartaporte31:IdentificacionVehicular AnioModeloVM="2020" ConfigVehicular="T3S1" PlacaVM="ABC123" PesoBrutoVehicular="2.0"/>
                                <cartaporte31:Seguros AseguraRespCivil="DEMO INSURER" PolizaRespCivil="DEMO POLICY"/>
                                <cartaporte31:Remolques>
                                    <cartaporte31:Remolque SubTipoRem="CTR003" Placa="trail1"/>
                                </cartaporte31:Remolques>
                            </cartaporte31:Autotransporte>
                        </cartaporte31:Mercancias>
                        <cartaporte31:FiguraTransporte>
                            <cartaporte31:TiposFigura TipoFigura="01" RFCFigura="VAAM130719H60" NumLicencia="a234567890" NombreFigura="Amigo Pedro">
                            </cartaporte31:TiposFigura>
                            <cartaporte31:TiposFigura TipoFigura="02" RFCFigura="EKU9003173C9" NombreFigura="ESCUELA KEMPER URGATE">
                                <cartaporte31:PartesTransporte ParteTransporte="PT05"/>
                            </cartaporte31:TiposFigura>
                        </cartaporte31:FiguraTransporte>
                    </cartaporte31:CartaPorte>
                </cfdi:Complemento>
            </cfdi:Comprobante>
        """

        current_etree = self.get_xml_tree_from_string(picking._l10n_mx_edi_create_delivery_guide())
        expected_etree = self.get_xml_tree_from_string(expected_cfdi)
        self.assertXmlTreeEqual(current_etree, expected_etree)

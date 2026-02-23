"""
Wrapper de pyafipws.wsfev1 para facturación electrónica
"""
from pyafipws.wsfev1 import WSFEv1
from ..config import settings
from ..services.afip_auth import get_ticket_acceso
from ..models.factura import FacturaCreate, FacturaCCreate, FacturaResponse, PuntoVenta, IVACondition
from typing import Optional, List
import re


class WSFEv1Service:
    """Servicio para operaciones de WSFEv1"""
    
    def __init__(self, env: str = "homo"):
        self.env = env
        self.wsfev1 = WSFEv1()
        self._conectar()
    
    def _conectar(self):
        """Conecta a WSFEv1 y obtiene ticket de acceso
        
        Orden de operaciones (siguiendo el patrón del script que funciona):
        1. Conectar primero (sin configurar CUIT ni ticket)
        2. Luego configurar SetTicketAcceso
        3. Finalmente configurar CUIT
        """
        print(f"[WSFEv1Service] Conectando en ambiente: {self.env}")
        
        # Obtener ticket de acceso (XML completo del TA)
        ta = get_ticket_acceso("wsfe", env=self.env)
        
        # Configurar paths
        cert_path, key_path = settings.get_cert_paths(self.env)
        cache_path = settings.get_cache_path(self.env)
        wsdl = settings.get_wsfev1_wsdl(self.env)
        
        print(f"[WSFEv1Service] CUIT: {settings.CUIT}")
        print(f"[WSFEv1Service] Cert: {cert_path}")
        print(f"[WSFEv1Service] Key: {key_path}")
        print(f"[WSFEv1Service] WSDL: {wsdl}")
        print(f"[WSFEv1Service] Cache: {cache_path}")
        
        # 1. Conectar PRIMERO (sin configurar CUIT ni ticket todavía)
        ok = self.wsfev1.Conectar(cache=str(cache_path), wsdl=wsdl)
        if not ok:
            error_msg = "No se pudo conectar a WSFEv1"
            if hasattr(self.wsfev1, 'Excepcion') and self.wsfev1.Excepcion:
                error_msg += f": {self.wsfev1.Excepcion}"
            raise Exception(error_msg)
        
        # 2. Luego configurar ticket de acceso
        self.wsfev1.SetTicketAcceso(ta)  # SetTicketAcceso espera el XML completo
        
        # 3. Finalmente configurar CUIT
        self.wsfev1.Cuit = settings.CUIT
        
        print(f"[WSFEv1Service] Conexión establecida")
    
    def obtener_ultimo_autorizado(self, tipo_cbte: int, punto_vta: int) -> int:
        """
        Obtiene el último número de comprobante autorizado
        
        Args:
            tipo_cbte: Tipo de comprobante
            punto_vta: Punto de venta
        
        Returns:
            Último número autorizado (0 si no hay comprobantes previos)
        
        Raises:
            Exception: Si falla la consulta
        """
        ultimo = self.wsfev1.CompUltimoAutorizado(tipo_cbte, punto_vta)
        
        # Verificar si hubo error
        err_msg = getattr(self.wsfev1, 'ErrMsg', None)
        err_code = getattr(self.wsfev1, 'ErrCode', None)
        excepcion = getattr(self.wsfev1, 'Excepcion', None)
        
        if excepcion:
            raise Exception(f"Error al obtener último autorizado: {excepcion} ({err_msg})")
        
        # Si ultimo es None o vacío, significa que no hay comprobantes previos
        # En ese caso, el siguiente número será 1
        if ultimo is None or ultimo == "":
            # Verificar si hay un error real o simplemente no hay comprobantes
            if err_code and err_code != "0":
                raise Exception(f"Error al obtener último autorizado: {err_msg} (Código: {err_code})")
            # No hay comprobantes previos, retornar 0 para que el siguiente sea 1
            return 0
        
        try:
            return int(ultimo)
        except (ValueError, TypeError):
            # Si no se puede convertir a int, asumir que no hay comprobantes previos
            if err_code and err_code != "0":
                raise Exception(f"Error al obtener último autorizado: {err_msg} (Código: {err_code})")
            return 0
    

    

    def emitir_factura(self, factura: FacturaCreate) -> FacturaResponse:
        """
        Emite una factura electrónica
        
        Args:
            factura: Datos de la factura
        
        Returns:
            Response con CAE y datos de la factura emitida
        
        Raises:
            Exception: Si falla la emisión
        """
        # Obtener último autorizado
        ultimo = self.obtener_ultimo_autorizado(factura.tipo_cbte, factura.punto_vta)
        # Si ultimo es 0, significa que no hay comprobantes previos, el siguiente es 1
        cbte_nro = ultimo + 1
        
        print(f"[emitir_factura] Tipo: {factura.tipo_cbte}, Punto Vta: {factura.punto_vta}")
        print(f"[emitir_factura] Último autorizado: {ultimo}, Siguiente número: {cbte_nro}")
        print(f"[emitir_factura] Fecha comprobante: {factura.fecha_cbte}")
        
        # Determinar condicion_iva_receptor_id
        # Si no se especifica, usar valor por defecto según tipo_doc
        # 5 = Consumidor Final (para tipo_doc=99)
        condicion_iva = factura.condicion_iva_receptor_id
        if condicion_iva is None:
            if factura.tipo_doc == 99:
                # Consumidor Final → Condición IVA 5
                condicion_iva = 5
            else:
                # Para otros tipos de documento, requerir explícitamente
                raise ValueError(
                    "condicion_iva_receptor_id es obligatorio según RG 5616. "
                    "Para tipo_doc=99 (Consumidor Final) usar: condicion_iva_receptor_id=5"
                )
        
        # Crear factura
        self.wsfev1.CrearFactura(
            concepto=factura.concepto,
            tipo_doc=factura.tipo_doc,
            nro_doc=factura.nro_doc,
            tipo_cbte=factura.tipo_cbte,
            punto_vta=factura.punto_vta,
            cbt_desde=cbte_nro,
            cbt_hasta=cbte_nro,
            imp_total=factura.imp_total,
            imp_tot_conc=factura.imp_tot_conc,
            imp_neto=factura.imp_neto,
            imp_iva=factura.imp_iva,
            imp_trib=factura.imp_trib,
            imp_op_ex=factura.imp_op_ex,
            fecha_cbte=factura.fecha_cbte,
            moneda_id=factura.moneda_id,
            moneda_ctz=factura.moneda_ctz,
            condicion_iva_receptor_id=condicion_iva,
        )

        if float(factura.imp_neto or 0) > 0:
            if not factura.iva:
                raise ValueError(
                    "Si imp_neto > 0, AFIP requiere enviar el objeto IVA (campo 'iva') con alícuotas. "
                    "Ejemplo: iva=[{iva_id: 5, base_imp: 100.0, importe: 21.0}]"
                )
            for alic in factura.iva:
                self.wsfev1.AgregarIva(
                    iva_id=alic.iva_id,
                    base_imp=alic.base_imp,
                    importe=alic.importe,
                )

        # Agregar comprobantes asociados (obligatorio para NC/ND)
        if factura.cbtes_asoc:
            for cbte_asoc in factura.cbtes_asoc:
                self.wsfev1.AgregarCmpAsoc(
                    tipo=cbte_asoc.tipo,
                    pto_vta=cbte_asoc.pto_vta,
                    nro=cbte_asoc.nro,
                    cuit=cbte_asoc.cuit if cbte_asoc.cuit else None,
                    fecha=cbte_asoc.fecha if cbte_asoc.fecha else None
                )
        
        # Solicitar CAE
        cae = self.wsfev1.CAESolicitar()
        
        # Extraer TODA la información disponible de la respuesta de AFIP
        resultado = getattr(self.wsfev1, "Resultado", "")
        vencimiento = getattr(self.wsfev1, "Vencimiento", "")
        cbte_nro_resp = getattr(self.wsfev1, "CbteNro", None)
        fecha_cbte = getattr(self.wsfev1, "FechaCbte", None)
        emision_tipo = getattr(self.wsfev1, "EmisionTipo", None)
        punto_venta = getattr(self.wsfev1, "PuntoVenta", None)
        cbt_desde = getattr(self.wsfev1, "CbtDesde", None)
        cbt_hasta = getattr(self.wsfev1, "CbtHasta", None)
        reproceso = getattr(self.wsfev1, "Reproceso", None)
        obs = getattr(self.wsfev1, "Obs", []) or []
        err_msg = getattr(self.wsfev1, "ErrMsg", None)
        err_code = getattr(self.wsfev1, "ErrCode", None)
        
        # Convertir obs a lista de strings si es necesario
        if obs and isinstance(obs, str):
            obs = [obs]
        
        # Convertir fechas vacías a None
        fecha_cbte = fecha_cbte if fecha_cbte else None
        vencimiento = vencimiento if vencimiento else None
        
        return FacturaResponse(
            resultado=resultado,
            cae=str(cae) if cae else None,
            vencimiento=vencimiento,
            cbte_nro=cbte_nro_resp if cbte_nro_resp is not None else cbte_nro,
            fecha_cbte=fecha_cbte,
            emision_tipo=emision_tipo,
            punto_venta=int(punto_venta) if punto_venta is not None else factura.punto_vta,
            cbt_desde=int(cbt_desde) if cbt_desde is not None else None,
            cbt_hasta=int(cbt_hasta) if cbt_hasta is not None else None,
            tipo_cbte=factura.tipo_cbte,  # Del request original
            reproceso=reproceso if reproceso else None,
            obs=obs if isinstance(obs, list) else [],
            err_msg=err_msg,
            err_code=str(err_code) if err_code else None
        )
    
    def emitir_factura_c(self, factura: FacturaCCreate) -> FacturaResponse:
        """Emite una Factura C (tipo_cbte=11)"""
        tipo_cbte = 11

        # Obtener último autorizado
        ultimo = self.obtener_ultimo_autorizado(tipo_cbte, factura.punto_vta)
        # Si ultimo es 0, significa que no hay comprobantes previos, el siguiente es 1
        cbte_nro = ultimo + 1
        
        print(f"[emitir_factura_c] Tipo: {tipo_cbte}, Punto Vta: {factura.punto_vta}")
        print(f"[emitir_factura_c] Último autorizado: {ultimo}, Siguiente número: {cbte_nro}")
        print(f"[emitir_factura_c] Fecha comprobante: {factura.fecha_cbte}")

        # Condición IVA receptor: por defecto Consumidor Final (5)
        condicion_iva = factura.condicion_iva_receptor_id
        if condicion_iva is None:
            if factura.tipo_doc == 99:
                condicion_iva = 5
            else:
                raise ValueError(
                    "condicion_iva_receptor_id es obligatorio según RG 5616. "
                    "Para tipo_doc=99 (Consumidor Final) usar: condicion_iva_receptor_id=5"
                )

        # Factura C típicamente no discrimina IVA en la cabecera
        imp_iva = 0.0

        self.wsfev1.CrearFactura(
            concepto=factura.concepto,
            tipo_doc=factura.tipo_doc,
            nro_doc=factura.nro_doc,
            tipo_cbte=tipo_cbte,
            punto_vta=factura.punto_vta,
            cbt_desde=cbte_nro,
            cbt_hasta=cbte_nro,
            imp_total=factura.imp_total,
            imp_tot_conc=factura.imp_tot_conc,
            imp_neto=factura.imp_neto,
            imp_iva=imp_iva,
            imp_trib=factura.imp_trib,
            imp_op_ex=factura.imp_op_ex,
            fecha_cbte=factura.fecha_cbte,
            moneda_id=factura.moneda_id,
            moneda_ctz=factura.moneda_ctz,
            condicion_iva_receptor_id=condicion_iva,
        )

        cae = self.wsfev1.CAESolicitar()

        resultado = getattr(self.wsfev1, "Resultado", "")
        vencimiento = getattr(self.wsfev1, "Vencimiento", "")
        cbte_nro_resp = getattr(self.wsfev1, "CbteNro", None)
        fecha_cbte = getattr(self.wsfev1, "FechaCbte", None)
        emision_tipo = getattr(self.wsfev1, "EmisionTipo", None)
        punto_venta = getattr(self.wsfev1, "PuntoVenta", None)
        cbt_desde = getattr(self.wsfev1, "CbtDesde", None)
        cbt_hasta = getattr(self.wsfev1, "CbtHasta", None)
        reproceso = getattr(self.wsfev1, "Reproceso", None)
        obs = getattr(self.wsfev1, "Obs", []) or []
        err_msg = getattr(self.wsfev1, "ErrMsg", None)
        err_code = getattr(self.wsfev1, "ErrCode", None)

        if obs and isinstance(obs, str):
            obs = [obs]

        fecha_cbte = fecha_cbte if fecha_cbte else None
        vencimiento = vencimiento if vencimiento else None

        return FacturaResponse(
            resultado=resultado,
            cae=str(cae) if cae else None,
            vencimiento=vencimiento,
            cbte_nro=cbte_nro_resp if cbte_nro_resp is not None else cbte_nro,
            fecha_cbte=fecha_cbte,
            emision_tipo=emision_tipo,
            punto_venta=int(punto_venta) if punto_venta is not None else factura.punto_vta,
            cbt_desde=int(cbt_desde) if cbt_desde is not None else None,
            cbt_hasta=int(cbt_hasta) if cbt_hasta is not None else None,
            tipo_cbte=tipo_cbte,
            reproceso=reproceso if reproceso else None,
            obs=obs if isinstance(obs, list) else [],
            err_msg=err_msg,
            err_code=str(err_code) if err_code else None,
        )
    
    def obtener_puntos_venta(self) -> List[PuntoVenta]:
        """
        Obtiene la lista de puntos de venta registrados
        
        Returns:
            Lista de puntos de venta (puede estar vacía si no hay puntos de venta)
        
        Raises:
            Exception: Si falla la consulta
        """
        # Verificar si hay excepciones antes de llamar
        excepcion = getattr(self.wsfev1, "Excepcion", None)
        
        # ParamGetPtosVenta retorna lista de strings con formato:
        # Por defecto usa sep="|", entonces: "Nro|EmisionTipo:X|Bloqueado:Y|FchBaja:Z"
        # Si pasamos sep="\t", entonces: "Nro\tEmisionTipo:X\tBloqueado:Y\tFchBaja:Z"
        # Usamos "\t" para mantener compatibilidad con el parseo existente
        ptos_vta_raw = self.wsfev1.ParamGetPtosVenta(sep="\t")

        
        
        # Verificar si hubo un error después de la llamada
        excepcion_despues = getattr(self.wsfev1, "Excepcion", None)
        err_msg = getattr(self.wsfev1, "ErrMsg", None)
        
        # Si hay excepción o error, lanzar excepción
        if excepcion_despues:
            error_text = f"Error al obtener puntos de venta: {excepcion_despues}"
            if err_msg:
                error_text += f" ({err_msg})"
            raise Exception(error_text)
        
        # Si ptos_vta_raw es None (no lista), también es un error
        if ptos_vta_raw is None:
            error_text = "Error al obtener puntos de venta: Respuesta None de AFIP"
            if err_msg:
                error_text += f" ({err_msg})"
            raise Exception(error_text)
        
        # Si ptos_vta_raw es lista vacía, está bien (puede no haber puntos de venta)
        # Pero verificar si hay algún error
        if ptos_vta_raw == [] and err_msg:
            raise Exception(f"Error al obtener puntos de venta: {err_msg}")
        
        # Debug: Si la lista está vacía sin errores, puede ser que no haya puntos de venta
        # o que la respuesta de AFIP esté vacía (caso válido)
        
        puntos_venta = []
        
        # Si ptos_vta_raw está vacío, retornar lista vacía (puede ser válido)
        if not ptos_vta_raw:
            return puntos_venta

        for pto_str in ptos_vta_raw:
            # Parsear string: "1\tEmisionTipo:CAE\tBloqueado:No\tFchBaja:"
            parts = pto_str.split("\t")
            
            # Extraer número (primer elemento)
            nro_str = parts[0] if parts else "0"
            try:
                nro = int(nro_str)
            except (ValueError, IndexError):
                continue
            
            # Extraer otros campos
            emision_tipo = None
            bloqueado = None
            fch_baja = None
            
            for part in parts[1:]:
                if "EmisionTipo:" in part:
                    emision_tipo = part.split("EmisionTipo:", 1)[1].strip() or None
                elif "Bloqueado:" in part:
                    bloqueado = part.split("Bloqueado:", 1)[1].strip() or None
                elif "FchBaja:" in part:
                    fch_baja_str = part.split("FchBaja:", 1)[1].strip()
                    fch_baja = fch_baja_str if fch_baja_str else None
            
            puntos_venta.append(PuntoVenta(
                nro=nro,
                emision_tipo=emision_tipo,
                bloqueado=bloqueado,
                fch_baja=fch_baja
            ))
        
        return puntos_venta

    def obtener_condiciones_iva_receptor(self, clase_cmp: str = "A") -> List[IVACondition]:
        """
        Obtiene la lista de condiciones de IVA de receptores válidas
        
        Webservice usado: WSFEv1 (Web Service de Factura Electrónica Versión 1)
        URL: https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL (homologación)
        Método: FEParamGetCondicionIvaReceptor
        
        Args:
            clase_cmp: Clase de comprobante (A, B, C, M, etc.)
        
        Returns:
            Lista de condiciones de IVA
        """
        # Acceder directamente a la respuesta SOAP para obtener todos los campos
        # incluyendo FchDesde y FchHasta si están disponibles
        ret = self.wsfev1.client.FEParamGetCondicionIvaReceptor(
            Auth={'Token': self.wsfev1.Token, 'Sign': self.wsfev1.Sign, 'Cuit': self.wsfev1.Cuit},
            ClaseCmp=clase_cmp,
        )
        
        excepcion = getattr(self.wsfev1, "Excepcion", None)
        err_msg = getattr(self.wsfev1, "ErrMsg", None)
        
        if excepcion:
            raise Exception(f"Error al obtener condiciones IVA: {excepcion} ({err_msg})")
        
        res = ret.get('FEParamGetCondicionIvaReceptorResult', {})
        result_get = res.get('ResultGet', [])
        
        if result_get is None:
            raise Exception(f"Respuesta None de AFIP al obtener condiciones IVA ({err_msg})")

        if result_get == []:
            return []  # Retornar lista vacía si no hay condiciones

        condiciones = []
        for p in result_get:
            cond = p.get('CondicionIvaReceptor', {})
            if not cond:
                continue
            
            try:
                id_cond = int(cond.get('Id', 0))
            except (ValueError, TypeError):
                continue
            
            desc = cond.get('Desc', '') or ''
            fch_desde = cond.get('FchDesde') or None
            fch_hasta = cond.get('FchHasta') or None
                    
            condiciones.append(IVACondition(
                id=id_cond,
                desc=desc,
                fch_desde=fch_desde,
                fch_hasta=fch_hasta
            ))
            
        return condiciones
    
    def consultar_comprobante(self, tipo_cbte: int, punto_vta: int, cbte_nro: int) -> dict:
        """
        Consulta un comprobante existente en AFIP (CompConsultar).
        
        Devuelve todos los datos del comprobante, incluyendo los necesarios
        para crear una Nota de Crédito/Débito basada en este comprobante.
        """
        self.wsfev1.CompConsultar(tipo_cbte, punto_vta, cbte_nro)

        resultado = getattr(self.wsfev1, "Resultado", None)
        cae = getattr(self.wsfev1, "CAE", None)
        vencimiento = getattr(self.wsfev1, "Vencimiento", None)
        fecha_cbte = getattr(self.wsfev1, "FechaCbte", None)
        reproceso = getattr(self.wsfev1, "Reproceso", None)
        obs = getattr(self.wsfev1, "Obs", []) or []
        err_msg = getattr(self.wsfev1, "ErrMsg", None)
        err_code = getattr(self.wsfev1, "ErrCode", None)

        if obs and isinstance(obs, str):
            obs = [obs]

        # Obtener datos adicionales desde factura (disponibles después de CompConsultar)
        factura = getattr(self.wsfev1, "factura", {}) or {}
        
        # Procesar comprobantes asociados si existen
        cbtes_asoc = []
        if factura.get("cbtes_asoc"):
            for cbte_asoc in factura["cbtes_asoc"]:
                cbtes_asoc.append({
                    "tipo": cbte_asoc.get("tipo"),
                    "pto_vta": cbte_asoc.get("pto_vta"),
                    "nro": cbte_asoc.get("nro"),
                    "cuit": cbte_asoc.get("cuit"),
                    "fecha": cbte_asoc.get("fecha"),
                })

        return {
            "tipo_cbte": int(tipo_cbte),
            "punto_vta": int(punto_vta),
            "cbte_nro": int(cbte_nro),
            "resultado": resultado if resultado else None,
            "cae": str(cae) if cae else None,
            "vencimiento": str(vencimiento) if vencimiento else None,
            "fecha_cbte": str(fecha_cbte) if fecha_cbte else None,
            "reproceso": str(reproceso) if reproceso else None,
            "obs": obs if isinstance(obs, list) else [],
            "err_msg": str(err_msg) if err_msg else None,
            "err_code": str(err_code) if err_code else None,
            # Campos adicionales para Nota de Crédito/Débito
            "concepto": factura.get("concepto"),
            "tipo_doc": factura.get("tipo_doc"),
            "nro_doc": str(factura.get("nro_doc")) if factura.get("nro_doc") is not None else None,
            "imp_total": float(factura.get("imp_total")) if factura.get("imp_total") is not None else None,
            "imp_neto": float(factura.get("imp_neto")) if factura.get("imp_neto") is not None else None,
            "imp_iva": float(factura.get("imp_iva")) if factura.get("imp_iva") is not None else None,
            "imp_tot_conc": float(factura.get("imp_tot_conc")) if factura.get("imp_tot_conc") is not None else None,
            "imp_trib": float(factura.get("imp_trib")) if factura.get("imp_trib") is not None else None,
            "imp_op_ex": float(factura.get("imp_op_ex")) if factura.get("imp_op_ex") is not None else None,
            "moneda_id": factura.get("moneda_id"),
            "moneda_ctz": str(factura.get("moneda_ctz")) if factura.get("moneda_ctz") is not None else None,
            "cbtes_asoc": cbtes_asoc,
        }
    
    def obtener_xml_response(self) -> Optional[str]:
        """
        Obtiene el XML de la última respuesta SOAP del webservice
        
        Webservice: WSFEv1 (Web Service de Factura Electrónica Versión 1)
        URL: https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL (homologación)
        
        Returns:
            XML de respuesta como string, o None si no está disponible
        """
        try:
            xml_response = getattr(self.wsfev1.client, 'xml_response', None)
            if xml_response and isinstance(xml_response, bytes):
                return xml_response.decode('utf-8', errors='ignore')
            return xml_response
        except Exception:
            return None

    def obtener_xml_response_bytes(self) -> Optional[bytes]:
        """Obtiene el XML de la última respuesta SOAP sin decodificar."""
        try:
            return getattr(self.wsfev1.client, 'xml_response', None)
        except Exception:
            return None
    
    def obtener_tipos_comprobante(self) -> List[dict]:
        """
        Obtiene la lista de tipos de comprobante disponibles
        
        Returns:
            Lista de diccionarios con id, desc, fch_desde, fch_hasta
        """
        # ParamGetTiposCbte retorna lista de strings con formato: "Id\tDesc\tFchDesde\tFchHasta"
        tipos_raw = self.wsfev1.ParamGetTiposCbte(sep="\t")
        
        excepcion = getattr(self.wsfev1, "Excepcion", None)
        err_msg = getattr(self.wsfev1, "ErrMsg", None)
        
        if excepcion:
            raise Exception(f"Error al obtener tipos de comprobante: {excepcion} ({err_msg})")
        
        if tipos_raw is None:
            raise Exception(f"Error al obtener tipos de comprobante: Respuesta None de AFIP ({err_msg})")
        
        tipos = []
        for tipo_str in tipos_raw:
            partes = tipo_str.split("\t")
            if len(partes) >= 2:
                tipos.append({
                    "id": int(partes[0]) if partes[0].isdigit() else partes[0],
                    "desc": partes[1] if len(partes) > 1 else "",
                    "fch_desde": partes[2] if len(partes) > 2 and partes[2] else None,
                    "fch_hasta": partes[3] if len(partes) > 3 and partes[3] else None,
                })
        
        return tipos
    
    def obtener_tipos_documento(self) -> List[dict]:
        """
        Obtiene la lista de tipos de documento disponibles
        
        Returns:
            Lista de diccionarios con id, desc, fch_desde, fch_hasta
        """
        tipos_raw = self.wsfev1.ParamGetTiposDoc(sep="\t")
        
        excepcion = getattr(self.wsfev1, "Excepcion", None)
        err_msg = getattr(self.wsfev1, "ErrMsg", None)
        
        if excepcion:
            raise Exception(f"Error al obtener tipos de documento: {excepcion} ({err_msg})")
        
        if tipos_raw is None:
            raise Exception(f"Error al obtener tipos de documento: Respuesta None de AFIP ({err_msg})")
        
        tipos = []
        for tipo_str in tipos_raw:
            partes = tipo_str.split("\t")
            if len(partes) >= 2:
                tipos.append({
                    "id": int(partes[0]) if partes[0].isdigit() else partes[0],
                    "desc": partes[1] if len(partes) > 1 else "",
                    "fch_desde": partes[2] if len(partes) > 2 and partes[2] else None,
                    "fch_hasta": partes[3] if len(partes) > 3 and partes[3] else None,
                })
        
        return tipos
    
    def obtener_tipos_iva(self) -> List[dict]:
        """
        Obtiene la lista de tipos de IVA (alícuotas) disponibles
        
        Returns:
            Lista de diccionarios con id, desc, fch_desde, fch_hasta
        """
        tipos_raw = self.wsfev1.ParamGetTiposIva(sep="\t")
        
        excepcion = getattr(self.wsfev1, "Excepcion", None)
        err_msg = getattr(self.wsfev1, "ErrMsg", None)
        
        if excepcion:
            raise Exception(f"Error al obtener tipos de IVA: {excepcion} ({err_msg})")
        
        if tipos_raw is None:
            raise Exception(f"Error al obtener tipos de IVA: Respuesta None de AFIP ({err_msg})")
        
        tipos = []
        for tipo_str in tipos_raw:
            partes = tipo_str.split("\t")
            if len(partes) >= 2:
                tipos.append({
                    "id": int(partes[0]) if partes[0].isdigit() else partes[0],
                    "desc": partes[1] if len(partes) > 1 else "",
                    "fch_desde": partes[2] if len(partes) > 2 and partes[2] else None,
                    "fch_hasta": partes[3] if len(partes) > 3 and partes[3] else None,
                })
        
        return tipos
    
    def obtener_tipos_concepto(self) -> List[dict]:
        """
        Obtiene la lista de tipos de concepto disponibles
        
        Returns:
            Lista de diccionarios con id, desc, fch_desde, fch_hasta
        """
        tipos_raw = self.wsfev1.ParamGetTiposConcepto(sep="\t")
        
        excepcion = getattr(self.wsfev1, "Excepcion", None)
        err_msg = getattr(self.wsfev1, "ErrMsg", None)
        
        if excepcion:
            raise Exception(f"Error al obtener tipos de concepto: {excepcion} ({err_msg})")
        
        if tipos_raw is None:
            raise Exception(f"Error al obtener tipos de concepto: Respuesta None de AFIP ({err_msg})")
        
        tipos = []
        for tipo_str in tipos_raw:
            partes = tipo_str.split("\t")
            if len(partes) >= 2:
                tipos.append({
                    "id": int(partes[0]) if partes[0].isdigit() else partes[0],
                    "desc": partes[1] if len(partes) > 1 else "",
                    "fch_desde": partes[2] if len(partes) > 2 and partes[2] else None,
                    "fch_hasta": partes[3] if len(partes) > 3 and partes[3] else None,
                })
        
        return tipos
    
    def obtener_estado_servidores(self) -> dict:
        """
        Obtiene el estado de los servidores de AFIP (Dummy)
        
        Returns:
            Diccionario con estado de AppServer, DbServer, AuthServer
        """
        ok = self.wsfev1.Dummy()
        
        excepcion = getattr(self.wsfev1, "Excepcion", None)
        err_msg = getattr(self.wsfev1, "ErrMsg", None)
        
        if excepcion:
            raise Exception(f"Error al obtener estado de servidores: {excepcion} ({err_msg})")
        
        if not ok:
            raise Exception(f"Error al obtener estado de servidores: {err_msg}")
        
        return {
            "app_server": getattr(self.wsfev1, "AppServerStatus", "Unknown"),
            "db_server": getattr(self.wsfev1, "DbServerStatus", "Unknown"),
            "auth_server": getattr(self.wsfev1, "AuthServerStatus", "Unknown"),
        }
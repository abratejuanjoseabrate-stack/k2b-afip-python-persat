from pyafipws.wsaa import WSAA
from pyafipws.wsfev1 import WSFEv1
from pyafipws.ws_sr_padron import WSSrPadronA5
from pysimplesoap.client import SoapFault

from datetime import datetime
import os
import re


# Homologación
URL_WSAA = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl"
URL_WSFEV1 = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"
URL_PADRON_A5 = "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA5?wsdl"


def _load_dotenv(env_path):
    if not os.path.exists(env_path):
        return {}
    data = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if "#" in v:
                v = v.split("#", 1)[0].strip()
            if k:
                data[k] = v
    return data


def _print_step(title):
    print("\n" + ("=" * 70))
    print(title)
    print(("=" * 70))


def _mask_secret(value, head=6, tail=6):
    if value is None:
        return ""
    s = str(value)
    if len(s) <= head + tail:
        return s
    return f"{s[:head]}...{s[-tail:]}"


def _mask_login_xml(xml_text):
    if not xml_text:
        return xml_text
    masked = re.sub(r"(<token>)(.*?)(</token>)", r"\1***\3", xml_text, flags=re.DOTALL)
    masked = re.sub(r"(<sign>)(.*?)(</sign>)", r"\1***\3", masked, flags=re.DOTALL)
    return masked


def _as_bool(value):
    return (str(value or "0").strip()) in ("1", "true", "True", "YES", "yes")


def _get_config(base_dir):
    env = _load_dotenv(os.path.join(base_dir, ".env"))

    cuit = int(env.get("CUIT", "0") or "0")
    if not cuit:
        raise RuntimeError("Falta configurar CUIT en afip_pruebas_wsfe/.env")

    pto_vta = int(env.get("PTO_VTA", "1") or "1")
    tipo_cbte = int(env.get("TIPO_CBTE", "6") or "6")
    print_ta = _as_bool(env.get("PRINT_TA", "0"))
    print_ta_full = _as_bool(env.get("PRINT_TA_FULL", "0"))
    print_login_xml = _as_bool(env.get("PRINT_LOGIN_XML", "0"))
    print_login_xml_full = _as_bool(env.get("PRINT_LOGIN_XML_FULL", "0"))

    cert = os.path.join(base_dir, "certs", "homo", "CERT.crt")
    privatekey = os.path.join(base_dir, "certs", "homo", "keyArca2")
    cache = os.path.join(base_dir, "cache")

    return {
        "env": env,
        "cuit": cuit,
        "pto_vta": pto_vta,
        "tipo_cbte": tipo_cbte,
        "print_ta": print_ta,
        "print_ta_full": print_ta_full,
        "print_login_xml": print_login_xml,
        "print_login_xml_full": print_login_xml_full,
        "cert": cert,
        "privatekey": privatekey,
        "cache": cache,
    }


def _ensure_paths(cert, privatekey, cache):
    if not os.path.exists(cert):
        raise FileNotFoundError(f"No existe el certificado: {cert}")
    if not os.path.exists(privatekey):
        raise FileNotFoundError(f"No existe la clave privada: {privatekey}")
    os.makedirs(cache, exist_ok=True)


def _auth_and_connect_padron(cfg):
    _print_step("CONFIG PADRON")
    print("CERT:", cfg["cert"])
    print("PRIVATEKEY:", cfg["privatekey"])
    print("CACHE DIR:", cfg["cache"])
    print("WSAA WSDL:", URL_WSAA)
    print("PADRON A5 WSDL:", URL_PADRON_A5)

    wsaa = WSAA()
    padron = WSSrPadronA5()

    _print_step("WSAA -> LoginCMS (service=ws_sr_padron_a5)")
    ta = wsaa.Autenticar(
        "ws_sr_padron_a5",
        cfg["cert"],
        cfg["privatekey"],
        wsdl=URL_WSAA,
        cache=cfg["cache"],
        debug=True,
    )
    print("TA obtenido (len):", len(ta) if ta else 0)

    if cfg["print_login_xml"]:
        _print_step("WSAA -> Respuesta LoginCMS (TA XML)")
        if cfg["print_login_xml_full"]:
            print(ta)
        else:
            print(_mask_login_xml(ta))

    if cfg["print_ta"]:
        token = getattr(wsaa, "Token", "")
        sign = getattr(wsaa, "Sign", "")
        if cfg["print_ta_full"]:
            print("WSAA Token:", token)
            print("WSAA Sign:", sign)
        else:
            print("WSAA Token:", _mask_secret(token))
            print("WSAA Sign:", _mask_secret(sign))

    _print_step("PADRON A5 -> Conectar")
    padron.Cuit = cfg["cuit"]
    padron.SetTicketAcceso(ta)
    padron.Conectar(cfg["cache"], None, cacert=None)  # homologación sin SSL verify
    return wsaa, padron, ta


def _test_padron_dummy(padron):
    _print_step("PADRON A5 -> Dummy")
    padron.Dummy()
    print("AppServerStatus:", padron.AppServerStatus)
    print("DbServerStatus:", padron.DbServerStatus)
    print("AuthServerStatus:", padron.AuthServerStatus)


def _test_padron_consultar(padron, cfg, cuit=None):
    _print_step("PADRON A5 -> Consultar")
    if cuit is None:
        cuit_input = input("CUIT a consultar (ej: 20129637979): ").strip()
        if not cuit_input:
            print("CUIT vacío, abortando.")
            return
        cuit = cuit_input
    print("Consultando CUIT:", cuit)
    try:
        ok = padron.Consultar(cuit)
    except SoapFault as e:
        print("SOAP Fault:", str(e))
        ok = False
    print("Resultado ok:", ok)
    print("Denominacion:", getattr(padron, "denominacion", ""))
    print("TipoPersona:", getattr(padron, "tipo_persona", ""))
    print("Estado:", getattr(padron, "estado", ""))
    print("Direccion:", getattr(padron, "direccion", ""))
    print("Localidad:", getattr(padron, "localidad", ""))
    print("Provincia:", getattr(padron, "provincia", ""))
    print("CodPostal:", getattr(padron, "cod_postal", ""))
    print("ImpIVA:", getattr(padron, "imp_iva", ""))
    print("Monotributo:", getattr(padron, "monotributo", ""))
    print("CatIVA:", getattr(padron, "cat_iva", ""))
    if getattr(padron, "Excepcion", ""):
        print("Excepcion:", padron.Excepcion)
    if cfg.get("print_soap", False):
        _print_step("PADRON A5 -> XML Request")
        print(getattr(padron, "XmlRequest", ""))
        _print_step("PADRON A5 -> XML Response")
        print(getattr(padron, "XmlResponse", ""))


def _run_menu_padron(padron, cfg):
    actions = {
        "1": ("Dummy", lambda: _test_padron_dummy(padron)),
        "2": (
            "Consultar (CUIT hardcodeado)",
            lambda: _test_padron_consultar(padron, cfg, cuit="20129637979"),
        ),
        "3": ("Consultar (ingresar CUIT)", lambda: _test_padron_consultar(padron, cfg)),
    }

    while True:
        _print_step("MENU PADRON A5")
        print("1) Dummy")
        print("2) Consultar (CUIT hardcodeado: 20129637979)")
        print("3) Consultar (ingresar CUIT)")
        print("0) Salir")
        choice = (input("Opcion: ") or "").strip()
        if choice in ("0", "q", "Q", "salir", "exit"):
            return
        action = actions.get(choice)
        if not action:
            print("Opcion invalida")
            continue
        _, fn = action
        fn()


def _auth_and_connect_wsfe(cfg):
    _print_step("CONFIG")
    print("CERT:", cfg["cert"])
    print("PRIVATEKEY:", cfg["privatekey"])
    print("CACHE DIR:", cfg["cache"])
    print("WSAA WSDL:", URL_WSAA)
    print("WSFEv1 WSDL:", URL_WSFEV1)

    wsaa = WSAA()
    wsfev1 = WSFEv1()

    _print_step("WSAA -> LoginCMS (service=wsfe)")
    ta = wsaa.Autenticar(
        "wsfe",
        cfg["cert"],
        cfg["privatekey"],
        wsdl=URL_WSAA,
        cache=cfg["cache"],
        debug=True,
    )
    print("TA obtenido (len):", len(ta) if ta else 0)

    if cfg["print_login_xml"]:
        _print_step("WSAA -> Respuesta LoginCMS (TA XML)")
        if cfg["print_login_xml_full"]:
            print(ta)
        else:
            print(_mask_login_xml(ta))

    if cfg["print_ta"]:
        token = getattr(wsaa, "Token", "")
        sign = getattr(wsaa, "Sign", "")
        if cfg["print_ta_full"]:
            print("WSAA Token:", token)
            print("WSAA Sign:", sign)
        else:
            print("WSAA Token:", _mask_secret(token))
            print("WSAA Sign:", _mask_secret(sign))

    _print_step("WSFEv1 -> Conectar")
    wsfev1.Cuit = cfg["cuit"]
    wsfev1.SetTicketAcceso(ta)
    wsfev1.Conectar(cfg["cache"], URL_WSFEV1)
    return wsaa, wsfev1, ta

    _print_step("WSAA -> LoginCMS (service=wsfe)")
    ta = wsaa.Autenticar(
        "wsfe",
        cfg["cert"],
        cfg["privatekey"],
        wsdl=URL_WSAA,
        cache=cfg["cache"],
        debug=True,
    )
    print("TA obtenido (len):", len(ta) if ta else 0)

    if cfg["print_login_xml"]:
        _print_step("WSAA -> Respuesta LoginCMS (TA XML)")
        if cfg["print_login_xml_full"]:
            print(ta)
        else:
            print(_mask_login_xml(ta))

    if cfg["print_ta"]:
        token = getattr(wsaa, "Token", "")
        sign = getattr(wsaa, "Sign", "")
        if cfg["print_ta_full"]:
            print("WSAA Token:", token)
            print("WSAA Sign:", sign)
        else:
            print("WSAA Token:", _mask_secret(token))
            print("WSAA Sign:", _mask_secret(sign))

    _print_step("WSFEv1 -> Conectar")
    wsfev1.Cuit = cfg["cuit"]
    wsfev1.SetTicketAcceso(ta)
    wsfev1.Conectar(cfg["cache"], URL_WSFEV1)
    return wsaa, wsfev1, ta


def _test_dummy(wsfev1):
    _print_step("WSFEv1 -> Dummy")
    wsfev1.Dummy()
    print("AppServerStatus:", wsfev1.AppServerStatus)
    print("DbServerStatus:", wsfev1.DbServerStatus)
    print("AuthServerStatus:", wsfev1.AuthServerStatus)


def _test_param_get_ptos_venta(wsfev1):
    _print_step("WSFEv1 -> ParamGetPtosVenta (FEParamGetPtosVenta)")
    ptos_vta = wsfev1.ParamGetPtosVenta()
    print("PtosVenta (count):", len(ptos_vta) if ptos_vta else 0)
    for row in (ptos_vta or [])[:10]:
        print("  ", row)


def _test_comp_ultimo_autorizado(wsfev1, tipo_cbte, pto_vta):
    _print_step("WSFEv1 -> CompUltimoAutorizado (FECompUltimoAutorizado)")
    ult = wsfev1.CompUltimoAutorizado(tipo_cbte, pto_vta)
    print("CompUltimoAutorizado:", "tipo_cbte=", tipo_cbte, "pto_vta=", pto_vta, "ult=", ult)


def _test_emitir_factura_c(wsfev1, cfg):
    _print_step("WSFEv1 -> Emitir Factura C (test)")

    env = cfg.get("env") or {}
    tipo_cbte = int(env.get("TEST_TIPO_CBTE", "11") or "11")  # 11: Factura C
    pto_vta = int(env.get("TEST_PTO_VTA", str(cfg["pto_vta"])) or cfg["pto_vta"])

    doc_tipo = int(env.get("TEST_DOC_TIPO", "99") or "99")  # 99: Consumidor Final
    doc_nro = int(env.get("TEST_DOC_NRO", "0") or "0")

    condicion_iva_receptor_id_raw = (env.get("TEST_CONDICION_IVA_RECEPTOR_ID", "") or "").strip()
    condicion_iva_receptor_id = (
        int(condicion_iva_receptor_id_raw) if condicion_iva_receptor_id_raw else None
    )

    imp_total = float(env.get("TEST_IMP_TOTAL", "100.00") or "100.00")

    ult = wsfev1.CompUltimoAutorizado(tipo_cbte, pto_vta)
    cbte_nro = int(ult or 0) + 1

    fecha_cbte = datetime.now().strftime("%Y%m%d")

    wsfev1.CrearFactura(
        concepto=1,
        tipo_doc=doc_tipo,
        nro_doc=str(doc_nro),
        tipo_cbte=tipo_cbte,
        punto_vta=pto_vta,
        cbt_desde=cbte_nro,
        cbt_hasta=cbte_nro,
        imp_total=imp_total,
        imp_tot_conc=0.00,
        imp_neto=imp_total,
        imp_iva=0.00,
        imp_trib=0.00,
        imp_op_ex=0.00,
        fecha_cbte=fecha_cbte,
        moneda_id="PES",
        moneda_ctz="1.0000",
        condicion_iva_receptor_id=condicion_iva_receptor_id,
    )

    cae = wsfev1.CAESolicitar()

    print("Resultado:", getattr(wsfev1, "Resultado", ""))
    print("CAE:", cae)
    print("Vencimiento:", getattr(wsfev1, "Vencimiento", ""))
    if getattr(wsfev1, "Obs", ""):
        print("Observaciones:", wsfev1.Obs)
    if getattr(wsfev1, "ErrMsg", ""):
        print("Errores:", wsfev1.ErrMsg)

    print("\n--- Detalle de la respuesta ---")
    print("CbteNro:", getattr(wsfev1, "CbteNro", ""))
    print("FechaCbte:", getattr(wsfev1, "FechaCbte", ""))
    print("EmisionTipo:", getattr(wsfev1, "EmisionTipo", ""))
    print("PuntoVenta:", getattr(wsfev1, "PuntoVenta", ""))
    print("CbtDesde:", getattr(wsfev1, "CbtDesde", ""))
    print("CbtHasta:", getattr(wsfev1, "CbtHasta", ""))

    print("\n--- Datos enviados ---")
    print("TipoCbte:", tipo_cbte)
    print("PtoVta:", pto_vta)
    print("CbteNro (calculado):", cbte_nro)
    print("DocTipo:", doc_tipo)
    print("DocNro:", doc_nro)
    print("CondicionIVAReceptorId:", condicion_iva_receptor_id)
    print("ImpTotal:", imp_total)
    print("FechaCbte (enviada):", fecha_cbte)


def _test_param_get_condicion_iva_receptor(wsfev1):
    _print_step("WSFEv1 -> ParamGetCondicionIvaReceptor")
    condiciones = wsfev1.ParamGetCondicionIvaReceptor()
    print("CondicionIvaReceptor (count):", len(condiciones) if condiciones else 0)
    for row in (condiciones or [])[:50]:
        print("  ", row)


def _test_comp_consultar(wsfev1, cfg):
    _print_step("WSFEv1 -> CompConsultar (FECompConsultar)")
    env = cfg.get("env") or {}
    tipo_cbte = int(env.get("TEST_CONS_TIPO_CBTE", str(cfg["tipo_cbte"])) or cfg["tipo_cbte"])
    pto_vta = int(env.get("TEST_CONS_PTO_VTA", str(cfg["pto_vta"])) or cfg["pto_vta"])
    cbte_nro_raw = (env.get("TEST_CONS_CBTE_NRO", "") or "").strip()
    if not cbte_nro_raw:
        raise RuntimeError("Falta TEST_CONS_CBTE_NRO en .env para consultar comprobante")
    cbte_nro = int(cbte_nro_raw)

    cae = wsfev1.CompConsultar(tipo_cbte, pto_vta, cbte_nro)
    print("CAE:", cae)
    print("Resultado:", getattr(wsfev1, "Resultado", ""))
    print("EmisionTipo:", getattr(wsfev1, "EmisionTipo", ""))
    print("CbteNro:", getattr(wsfev1, "CbteNro", ""))
    print("FechaCbte:", getattr(wsfev1, "FechaCbte", ""))
    print("Vencimiento:", getattr(wsfev1, "Vencimiento", ""))
    if getattr(wsfev1, "Obs", ""):
        print("Observaciones:", wsfev1.Obs)
    if getattr(wsfev1, "ErrMsg", ""):
        print("Errores:", wsfev1.ErrMsg)


def _run_menu(wsfev1, cfg):
    actions = {
        "1": ("Dummy", lambda: _test_dummy(wsfev1)),
        "2": ("ParamGetPtosVenta", lambda: _test_param_get_ptos_venta(wsfev1)),
        "3": (
            "CompUltimoAutorizado",
            lambda: _test_comp_ultimo_autorizado(wsfev1, cfg["tipo_cbte"], cfg["pto_vta"]),
        ),
        "4": ("Emitir Factura C (test)", lambda: _test_emitir_factura_c(wsfev1, cfg)),
        "5": (
            "ParamGetCondicionIvaReceptor",
            lambda: _test_param_get_condicion_iva_receptor(wsfev1),
        ),
        "6": ("CompConsultar", lambda: _test_comp_consultar(wsfev1, cfg)),
    }

    while True:
        _print_step("MENU")
        print("1) Dummy")
        print("2) ParamGetPtosVenta")
        print("3) CompUltimoAutorizado")
        print("4) Emitir Factura C (test)")
        print("5) ParamGetCondicionIvaReceptor")
        print("6) CompConsultar")
        print("0) Salir")
        choice = (input("Opcion: ") or "").strip()
        if choice in ("0", "q", "Q", "salir", "exit"):
            return
        action = actions.get(choice)
        if not action:
            print("Opcion invalida")
            continue
        _, fn = action
        fn()


def main_padron():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = _get_config(base_dir)
    _ensure_paths(cfg["cert"], cfg["privatekey"], cfg["cache"])
    _, padron, _ = _auth_and_connect_padron(cfg)
    _run_menu_padron(padron, cfg)


def main():
    import sys
    if "--padron" in sys.argv:
        main_padron()
        return
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = _get_config(base_dir)
    _ensure_paths(cfg["cert"], cfg["privatekey"], cfg["cache"])
    _, wsfev1, _ = _auth_and_connect_wsfe(cfg)
    _run_menu(wsfev1, cfg)


if __name__ == "__main__":
    main()

import re
F3 = "    include_tokenizador: Optional[bool] = False\n    include_link_pago: Optional[bool] = False\n    lp_standalone: Optional[bool] = False\n"
p = '/app/backend/models.py'
s = open(p).read()
lines = s.split('\n')
out = []
for i, ln in enumerate(lines):
    out.append(ln)
    if ln == "    servicio_express: Optional[bool] = False" and i < 830:
        out.append(F3.rstrip('\n'))
open(p, 'w').write('\n'.join(out))

p = '/app/backend/routes/quotes.py'
s = open(p).read()
def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (old, s.count(old))
    s = s.replace(old, new)
rep("    iva_exempt: Optional[bool] = False\n    servicio_express: Optional[bool] = False\n",
    "    iva_exempt: Optional[bool] = False\n    servicio_express: Optional[bool] = False\n" + F3)
rep("    iva_exempt: Optional[bool] = None\n    servicio_express: Optional[bool] = None\n",
    "    iva_exempt: Optional[bool] = None\n    servicio_express: Optional[bool] = None\n    include_tokenizador: Optional[bool] = None\n    include_link_pago: Optional[bool] = None\n    lp_standalone: Optional[bool] = None\n")
rep("        servicio_express=bool(quote_data.servicio_express),\n",
    "        servicio_express=bool(quote_data.servicio_express),\n        include_tokenizador=bool(quote_data.include_tokenizador),\n        include_link_pago=bool(quote_data.include_link_pago),\n        lp_standalone=bool(quote_data.lp_standalone),\n")
rep("            servicio_express=bool(data.servicio_express),\n",
    "            servicio_express=bool(data.servicio_express),\n            include_tokenizador=bool(data.include_tokenizador),\n            include_link_pago=bool(data.include_link_pago),\n            lp_standalone=bool(data.lp_standalone),\n")
rep("""            iva_exempt=bool(quote.get("iva_exempt", False)),
        )""", """            iva_exempt=bool(quote.get("iva_exempt", False)),
            include_tokenizador=bool(quote.get("include_tokenizador", False)),
            include_link_pago=bool(quote.get("include_link_pago", False)),
            lp_standalone=bool(quote.get("lp_standalone", False)),
        )""")
rep("""                pdf_request.iva_exempt = bool(data.iva_exempt)
""", """                pdf_request.iva_exempt = bool(data.iva_exempt)
                pdf_request.include_tokenizador = bool(data.include_tokenizador)
                pdf_request.include_link_pago = bool(data.include_link_pago)
                pdf_request.lp_standalone = bool(data.lp_standalone)
""")
# tokenizador billing line also for GATEWAY with include_tokenizador
rep("""    quote = await db.quotes.find_one({"quote_id": quote_id}, {"_id": 0, "quote_type": 1, "link_pago_variant": 1})
    if not quote:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    if (quote.get("quote_type") or "").upper() != "LINK_PAGO":
        return {"applies": False}
    variant = (quote.get("link_pago_variant") or "").lower()
    if variant not in ("tokenizador", "ambos"):
        return {"applies": False}""", """    quote = await db.quotes.find_one({"quote_id": quote_id}, {"_id": 0, "quote_type": 1, "link_pago_variant": 1, "include_tokenizador": 1})
    if not quote:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    qt = (quote.get("quote_type") or "").upper()
    if qt == "GATEWAY":
        if not quote.get("include_tokenizador"):
            return {"applies": False}
    elif qt != "LINK_PAGO" or (quote.get("link_pago_variant") or "").lower() not in ("tokenizador", "ambos"):
        return {"applies": False}""")
open(p, 'w').write(s)

p = '/app/backend/routes/quote_transitions.py'
s = open(p).read()
rep("""    if _add_comp:
        project["additional_components"] = _add_comp""", """    if _add_comp is None and (quote.get("quote_type") or "").upper() == "GATEWAY" and (
        quote.get("include_tokenizador") or quote.get("include_link_pago")
    ):
        _add_comp = {
            "link_pago": bool(quote.get("include_link_pago")),
            "tokenizador": bool(quote.get("include_tokenizador")),
        }
    if _add_comp:
        project["additional_components"] = _add_comp""")
open(p, 'w').write(s)
print("ok")

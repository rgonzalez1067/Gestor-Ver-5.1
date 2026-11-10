"""Alcance jerárquico de cotizaciones VPOS/MPOS: Grupo → Marcas → RIFs → Sucursales.

scope_tree: [{client_id, rif, legal_name, marca_id, marca_name,
              stores: [{client_id, name, is_principal, boxes}]}]
"""
from html import escape

NIVELES = {"GRUPO": "Grupo Económico", "MARCA": "Marca", "RIF": "RIF"}
PATROCINIOS = {"BANCO": "Patrocinada por Banco/Ente", "CLIENTE": "Patrocinada por Cliente"}
SCOPE_INPUT_FIELDS = [
    "nivel_cotizacion", "grupo_economico_id", "grupo_economico_name", "scope_tree", "cajas_desglose",
    "patrocinador_tipo", "patrocinador_id", "patrocinador_nombre",
]


def _int(v) -> int:
    try:
        return max(int(v or 0), 0)
    except (TypeError, ValueError):
        return 0


def _k(s) -> str:
    return " ".join((s or "").split()).lower()


def sort_tree(tree: list) -> list:
    """Orden de estructura: Marca (A-Z, sin marca al final) → RIF (razón social) → Principal y sucursales (A-Z)."""
    for r in tree:
        r["stores"] = sorted(r.get("stores") or [], key=lambda s: (not s.get("is_principal"), _k(s.get("name"))))
    return sorted(tree, key=lambda r: (not r.get("marca_name"), _k(r.get("marca_name")), _k(r.get("legal_name")), r.get("rif") or ""))


def clean_tree(tree) -> list:
    out = []
    for r in tree or []:
        if not r.get("client_id"):
            continue
        stores = [{"client_id": s.get("client_id"), "name": s.get("name") or "Principal",
                   "is_principal": bool(s.get("is_principal")), "boxes": _int(s.get("boxes"))}
                  for s in (r.get("stores") or []) if s.get("client_id")]
        out.append({"client_id": r["client_id"], "rif": r.get("rif") or "", "legal_name": r.get("legal_name") or "",
                    "marca_id": r.get("marca_id") or None, "marca_name": r.get("marca_name") or "", "stores": stores})
    return sort_tree(out)


def infer_project_type(tree: list) -> str:
    if not tree:
        return ""
    marcas = {r.get("marca_id") for r in tree if r.get("marca_id")}
    stores = sum(max(len(r.get("stores") or []), 1) for r in tree)
    if len(marcas) > 1:
        return "Multi Marca"
    if len(tree) > 1:
        return "Multi RIF"
    if stores > 1:
        return "Multitienda"
    return "Monotienda"


def compute_scope(data: dict) -> dict:
    """Normaliza los campos de alcance y deriva tipología + detalle de sucursales."""
    out = {k: data.get(k) for k in SCOPE_INPUT_FIELDS if k in data}
    if "scope_tree" not in data:
        return out
    tree = clean_tree(data.get("scope_tree"))
    out["scope_tree"] = tree
    out["cajas_desglose"] = bool(data.get("cajas_desglose"))
    out["tipo_proyecto_inferido"] = infer_project_type(tree)
    out["cotizacion_sucursales"] = [
        {"rif_client_id": r["client_id"], "rif": r["rif"], "legal_name": r["legal_name"], "marca_name": r["marca_name"],
         "client_id": s["client_id"], "sucursal": s["name"], "cajas": s["boxes"] if out["cajas_desglose"] else 0}
        for r in tree for s in r["stores"]
    ]
    if out.get("patrocinador_tipo") not in PATROCINIOS:
        out["patrocinador_tipo"] = None
    return out


def total_store_boxes(tree: list) -> int:
    return sum(s.get("boxes", 0) for r in tree or [] for s in r.get("stores") or [])


def is_multi(tree: list) -> bool:
    return infer_project_type(tree) in ("Multi Marca", "Multi RIF", "Multitienda")


def to_distribution(tree: list, desglose: bool) -> list:
    """Formato `multirif_distribution` (PDF / proyecto) a partir del árbol."""
    dist = []
    for r in sort_tree([dict(x) for x in tree or []]):
        stores = [{"name": s.get("name", ""), "boxes": _int(s.get("boxes")) if desglose else 0} for s in r.get("stores") or []]
        label = r.get("legal_name") or r.get("rif")
        if r.get("marca_name"):
            label = f"{r['marca_name']} · {label}"
        dist.append({"client_id": r["client_id"], "rif": r.get("rif"), "client_name": label,
                     "marca_name": r.get("marca_name"), "boxes": sum(s["boxes"] for s in stores), "stores": stores})
    return dist


def _scope_matrix_html(quote: dict) -> str:
    tree = sort_tree([dict(x) for x in (quote.get("scope_tree") or [])])
    if not tree:
        return ""
    desglose = quote.get("cajas_desglose")
    th = 'style="background:#1e3a8a;color:#fff;padding:6px 8px;text-align:left;font-size:12px;"'
    td = 'style="border:1px solid #cbd5e1;padding:5px 8px;font-size:12px;"'
    rows = []
    for r in tree:
        for s in r.get("stores") or []:
            rows.append(
                f"<tr><td {td}>{escape(r.get('marca_name') or '—')}</td><td {td}>{escape(r.get('rif') or '')} · {escape(r.get('legal_name') or '')}</td>"
                f"<td {td}>{escape(s.get('name') or '')}</td><td {td} align=\"center\">{s.get('boxes', 0) if desglose else '—'}</td></tr>"
            )
    total = total_store_boxes(tree) if desglose else (quote.get("cantidad_cajas") or 0)
    rows.append(f"<tr><td {td} colspan=\"3\"><b>Total Cajas</b></td><td {td} align=\"center\"><b>{total}</b></td></tr>")
    return (f"<table style=\"border-collapse:collapse;width:100%;font-family:Arial,sans-serif;\"><thead><tr>"
            f"<th {th}>Marca</th><th {th}>RIF / Razón Social</th><th {th}>Sucursal</th><th {th}>Cajas</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>")


def scope_template_vars(doc: dict) -> dict:
    """Variables de plantilla (cotización o proyecto con los mismos campos)."""
    tree = sort_tree([dict(x) for x in (doc.get("scope_tree") or [])])
    marcas = sorted({r.get("marca_name") for r in tree if r.get("marca_name")})
    patrocinio = doc.get("patrocinador_tipo")
    total = total_store_boxes(tree) if doc.get("cajas_desglose") else (doc.get("cantidad_cajas") or doc.get("box_count") or 0)
    return {
        "Nivel_Cotizacion": NIVELES.get(doc.get("nivel_cotizacion") or "", ""),
        "Grupo_Economico_Cotizacion": doc.get("grupo_economico_name") or "",
        "Marcas_Cotizacion": ", ".join(marcas),
        "RIFs_Cotizacion": ", ".join(f"{r.get('rif')} {r.get('legal_name')}".strip() for r in tree),
        "Sucursales_Cotizacion": ", ".join(s.get("name") for r in tree for s in r.get("stores") or []),
        "Cantidad_RIFs_Cotizacion": str(len(tree)) if tree else "",
        "Cantidad_Sucursales_Cotizacion": str(sum(len(r.get("stores") or []) for r in tree)) if tree else "",
        "Total_Cajas_Cotizacion": str(total) if tree else "",
        "Tipologia_Proyecto": doc.get("tipo_proyecto_inferido") or doc.get("tipologia_proyecto") or "",
        "Tipo_Patrocinio": PATROCINIOS.get(patrocinio or "", ""),
        "Patrocinador_Cotizacion": doc.get("patrocinador_nombre") or "",
        "Matriz_Alcance_Cotizacion": _scope_matrix_html(doc),
    }

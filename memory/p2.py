def R(p,a,b):
    s=open(p).read(); assert a in s,(p,a[:60]); s=s.replace(a,b,1); open(p,'w').write(s)
R('routes/quote_transitions.py','''    # ── FIX Monotienda: asignar la cantidad EXACTA de cajas cotizada por banco/producto ──''','''    # Alcance jerárquico VPOS/MPOS (Grupo → Marcas → RIFs → Sucursales): tipificación y árbol.
    scope_tree = quote.get("scope_tree") or []
    if scope_tree and not quote.get("is_multirif"):
        from services.quote_scope import infer_project_type, to_distribution
        tipologia = quote.get("tipo_proyecto_inferido") or infer_project_type(scope_tree)
        desglose = bool(quote.get("cajas_desglose"))
        for k in ("nivel_cotizacion", "grupo_economico_id", "grupo_economico_name", "patrocinador_tipo",
                  "patrocinador_id", "patrocinador_nombre"):
            project[k] = quote.get(k)
        project["scope_tree"] = scope_tree
        project["cajas_desglose"] = desglose
        project["tipologia_proyecto"] = tipologia
        if project["project_type"] == "single" and tipologia in ("Multi Marca", "Multi RIF"):
            project["project_type"] = "multirif"
            project["rifs"], project["stores"] = [], []
            for rif in to_distribution(scope_tree, desglose):
                rif_id = f"rif_{uuid.uuid4().hex[:8]}"
                project["rifs"].append({"rif_id": rif_id, "client_id": rif["client_id"], "rif": rif["rif"],
                                        "client_name": rif["client_name"], "marca_name": rif.get("marca_name"),
                                        "box_count": rif["boxes"], "status": "Pendiente"})
                for st in rif["stores"]:
                    project["stores"].append({"store_id": f"st_{uuid.uuid4().hex[:8]}", "rif_id": rif_id, "rif": rif["rif"],
                                              "client_name": rif["client_name"], "marca_name": rif.get("marca_name"),
                                              "name": st["name"], "box_count": st["boxes"],
                                              "implementation_matrix": copy.deepcopy(implementation_matrix),
                                              "status": "Pendiente", "notes": []})
        elif project["project_type"] == "single" and tipologia == "Multitienda":
            project["project_type"] = "multistore"
            project["stores"] = [{"store_id": f"st_{uuid.uuid4().hex[:8]}", "name": s.get("name", ""),
                                  "box_count": s.get("boxes", 0) if desglose else 0,
                                  "implementation_matrix": dict(implementation_matrix), "status": "Pendiente", "notes": []}
                                 for s in scope_tree[0].get("stores") or []]
        project["notes"].append({
            "note_id": f"pn_{uuid.uuid4().hex[:8]}",
            "text": f"Proyecto tipificado como {tipologia}: {len(scope_tree)} RIF(s), "
                    f"{sum(len(r.get('stores') or []) for r in scope_tree)} sucursal(es).",
            "created_by": "system", "created_by_name": "Sistema", "created_at": now.isoformat(),
        })

    # ── FIX Monotienda: asignar la cantidad EXACTA de cajas cotizada por banco/producto ──''')
R('services/quote_template_vars.py','''    return {
        "Matriz_Bancos_Productos": matriz_bancos,
        "Matriz_Sucursales": matriz_sucursales,
        "Patrocinador": patrocinador,
    }''','''    from services.quote_scope import scope_template_vars
    return {
        "Matriz_Bancos_Productos": matriz_bancos,
        "Matriz_Sucursales": matriz_sucursales,
        "Patrocinador": patrocinador,
        **scope_template_vars(quote),
    }''')
R('services/project_template_vars.py','''        "Tipo_Proyecto": project.get("quote_type", "") or "",''','''        "Tipo_Proyecto": project.get("quote_type", "") or "",
        **__import__("services.quote_scope", fromlist=["scope_template_vars"]).scope_template_vars(project),''')
R('routes/other_actions_config.py','''    "Matriz_Bancos_Productos", "Matriz_Sucursales",''','''    "Matriz_Bancos_Productos", "Matriz_Sucursales",
    "Nivel_Cotizacion", "Grupo_Economico_Cotizacion", "Marcas_Cotizacion", "RIFs_Cotizacion",
    "Sucursales_Cotizacion", "Cantidad_RIFs_Cotizacion", "Cantidad_Sucursales_Cotizacion", "Total_Cajas_Cotizacion",
    "Tipologia_Proyecto", "Tipo_Patrocinio", "Patrocinador_Cotizacion", "Matriz_Alcance_Cotizacion",''')
print('ok')

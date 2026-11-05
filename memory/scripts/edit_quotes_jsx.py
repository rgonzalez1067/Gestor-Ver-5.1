p = '/app/frontend/src/pages/Quotes.jsx'
s = open(p).read()
def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (old[:90], s.count(old))
    s = s.replace(old, new)

PAY = "        servicio_express: !!quoteData.servicio_express,\n"
PAY_NEW = PAY + "        include_tokenizador: quoteData.quote_type === 'GATEWAY' && !!quoteData.include_tokenizador,\n        include_link_pago: quoteData.quote_type === 'GATEWAY' && !!quoteData.include_link_pago,\n        lp_standalone: quoteData.quote_type === 'LINK_PAGO' && !!quoteData.lp_standalone,\n"
rep(PAY, PAY_NEW, 3)
rep("    iva_exempt: false,\n    servicio_express: false,\n  });", "    iva_exempt: false,\n    servicio_express: false,\n    include_tokenizador: false,\n    include_link_pago: false,\n    lp_standalone: false,\n  });")
rep("      iva_exempt: false,\n    servicio_express: false,\n    });", "      iva_exempt: false,\n    servicio_express: false,\n    include_tokenizador: false,\n    include_link_pago: false,\n    lp_standalone: false,\n    });")
rep("      servicio_express: !!quote.servicio_express || (quote.pg_setup_items || []).some(i => i.express),\n    });",
    "      servicio_express: !!quote.servicio_express || (quote.pg_setup_items || []).some(i => i.express),\n      include_tokenizador: !!quote.include_tokenizador,\n      include_link_pago: !!quote.include_link_pago,\n      lp_standalone: !!quote.lp_standalone,\n    });")
rep("      link_pago_variant: quoteData.link_pago_variant || 'link_pago',\n      pricing_model: quoteData.pricing_model,\n",
    "      link_pago_variant: quoteData.link_pago_variant || 'link_pago',\n      include_tokenizador: quoteData.quote_type === 'GATEWAY' && !!quoteData.include_tokenizador,\n      include_link_pago: quoteData.quote_type === 'GATEWAY' && !!quoteData.include_link_pago,\n      lp_standalone: quoteData.quote_type === 'LINK_PAGO' && !!quoteData.lp_standalone,\n      pricing_model: quoteData.pricing_model,\n")
rep("""  const handleSubmitPGQuote = async () => {
    if (pgSetupItems.length === 0) {""", """  const handleSubmitPGQuote = async () => {
    const isLpStandalone = quoteData.quote_type === 'LINK_PAGO' && !!quoteData.lp_standalone;
    if (!isLpStandalone && pgSetupItems.length === 0) {""")
rep("""        pg_setup_items: pgSetupItems.map(({ fixed, ...item }) => item), // Remove fixed flag
        servicio_express: !!quoteData.servicio_express,
        include_tokenizador""", """        pg_setup_items: isLpStandalone ? [] : pgSetupItems.map(({ fixed, ...item }) => item), // Remove fixed flag
        servicio_express: !!quoteData.servicio_express,
        include_tokenizador""")
rep("""        pg_recurring_cost: recurringData,
        pg_transaction_range: pgMediosPagoCount,""", """        pg_recurring_cost: isLpStandalone ? null : recurringData,
        pg_transaction_range: isLpStandalone ? 0 : pgMediosPagoCount,""")
open(p, 'w').write(s)
print('ok')

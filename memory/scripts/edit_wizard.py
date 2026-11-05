p = '/app/frontend/src/components/quotes/QuoteWizardDialog.jsx'
s = open(p).read()
def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (old[:90], s.count(old))
    s = s.replace(old, new)

rep("import { ExpressServiceToggle } from './ExpressServiceToggle';",
    "import { ExpressServiceToggle } from './ExpressServiceToggle';\nimport { PgAdditionalServicesToggles, LpStandaloneSummary } from './PgAdditionalServices';")
rep("    isLoadingEdit, editingQuoteId, currentUser,\n  } = ctx;\n",
    "    isLoadingEdit, editingQuoteId, currentUser,\n  } = ctx;\n  const isLpStandalone = quoteData.quote_type === 'LINK_PAGO' && !!quoteData.lp_standalone;\n")
rep("""                          link_pago_variant: value === 'LINK_PAGO' ? (quoteData.link_pago_variant || 'link_pago') : quoteData.link_pago_variant,
""", """                          link_pago_variant: value === 'LINK_PAGO' ? (quoteData.link_pago_variant || 'link_pago') : quoteData.link_pago_variant,
                          include_tokenizador: false,
                          include_link_pago: false,
                          lp_standalone: value === 'LINK_PAGO',
                          servicio_express: value === 'LINK_PAGO' ? false : quoteData.servicio_express,
""")
rep("""                        if (isPGLike) {
                          const pjService""", """                        if (value === 'GATEWAY') {
                          const pjService""")
rep("""                    {(isVPOS || isMPOS || isPaymentGateway) && (
                      <ExpressServiceToggle quoteData={quoteData} setQuoteData={setQuoteData} expressService={expressService} />
                    )}""", """                    {(isVPOS || isMPOS || (isPaymentGateway && !isLpStandalone)) && (
                      <ExpressServiceToggle quoteData={quoteData} setQuoteData={setQuoteData} expressService={expressService} />
                    )}
                    {quoteData.quote_type === 'GATEWAY' && (
                      <PgAdditionalServicesToggles quoteData={quoteData} setQuoteData={setQuoteData} />
                    )}""")
rep("""              {isPaymentGateway && isHeaderComplete && (
                <div className="bg-white rounded-lg p-5 border mt-4">
                  <h3 className="font-semibold text-lg text-slate-800 mb-4 flex items-center gap-2">
                    <span className="w-7 h-7 rounded-full bg-emerald-600""", """              {isPaymentGateway && !isLpStandalone && isHeaderComplete && (
                <div className="bg-white rounded-lg p-5 border mt-4">
                  <h3 className="font-semibold text-lg text-slate-800 mb-4 flex items-center gap-2">
                    <span className="w-7 h-7 rounded-full bg-emerald-600""")
rep("""              {isPaymentGateway && isHeaderComplete && pgRecurringCostsTable && (""",
    """              {isPaymentGateway && !isLpStandalone && isHeaderComplete && pgRecurringCostsTable && (""")
rep("""              {isPaymentGateway && isHeaderComplete && pgSetupItems.length > 0 && (""",
    """              {isLpStandalone && isHeaderComplete && (
                <LpStandaloneSummary variant={quoteData.link_pago_variant || 'link_pago'} onChangeVariant={() => setLinkPagoModal(true)} />
              )}
              {isPaymentGateway && isHeaderComplete && (pgSetupItems.length > 0 || isLpStandalone) && (""")
rep("""                <DialogDescription>
                  Esta selección determina la estructura de tarifas del PDF final.
                </DialogDescription>""", """                <DialogDescription>
                  Solo para clientes con Payment Gateway activo: el PDF incluirá únicamente las tarifas del servicio elegido, sin conceptos de Payment Gateway.
                </DialogDescription>""")
rep("""                  { id: 'link_pago', label: 'Link de Pago', desc: 'Tarifas de Link de Pago (5 páginas).' },
                  { id: 'tokenizador', label: 'Tokenizador', desc: 'Reemplaza las tarifas por las del Tokenizador (5 páginas).' },
                  { id: 'ambos', label: 'Link de Pago/Tokenizador', desc: 'Incluye ambas tablas de tarifas (6 páginas).' },""",
    """                  { id: 'link_pago', label: 'Link de Pago', desc: 'Solo las tarifas de Link de Pago.' },
                  { id: 'tokenizador', label: 'Tokenizador', desc: 'Solo las tarifas del Tokenizador.' },
                  { id: 'ambos', label: 'Link de Pago/Tokenizador', desc: 'Tarifas de Link de Pago y Tokenizador.' },""")
open(p, 'w').write(s)
print('ok')

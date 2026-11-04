export const PRODUCT_STATUSES = ['DESA', 'SQA', 'Imple', 'Primer Prod', 'Producción'];

export const getProductStatus = (p) => p?.operational_status || (p?.pre_production ? 'Imple' : 'Producción');

export const isPreProduction = (p) => getProductStatus(p) !== 'Producción';

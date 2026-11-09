import { useState, useEffect } from 'react';
import api from '../../../utils/api';

let cache = null;

export const useClientCatalogs = () => {
  const [cat, setCat] = useState(cache || { ejecutivos: [], coordinadores: [], implementadores: [], integrators: [], printers: [], categories: [] });
  useEffect(() => {
    if (cache) return;
    const get = (u) => api.get(u).then(r => r.data || []).catch(() => []);
    Promise.all([
      get('/auth/ejecutivos'), get('/auth/coordinadores'), get('/auth/implementadores'),
      get('/integrators/dropdown'), get('/fiscal-printers'), get('/commercial-categories?only_active=true'),
    ]).then(([ejecutivos, coordinadores, implementadores, integrators, printers, categories]) => {
      cache = { ejecutivos, coordinadores, implementadores, integrators, printers, categories };
      setCat(cache);
    });
  }, []);
  return cat;
};

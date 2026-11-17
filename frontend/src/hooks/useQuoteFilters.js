import { useState, useCallback } from 'react';

/**
 * Hook que centraliza los 6 filtros rápidos de la pantalla Cotizaciones
 * y un helper para limpiarlos todos.
 */
export function useQuoteFilters() {
  const [filterClient, setFilterClient] = useState('');
  const [filterGroup, setFilterGroup] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [filterSegment, setFilterSegment] = useState('');
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');
  const [filterBranch, setFilterBranch] = useState('');

  const clearFilters = useCallback(() => {
    setFilterClient('');
    setFilterGroup('');
    setFilterStatus('');
    setFilterCategory('');
    setFilterSegment('');
    setFilterDateFrom('');
    setFilterDateTo('');
    setFilterBranch('');
  }, []);

  return {
    filterClient, setFilterClient,
    filterGroup, setFilterGroup,
    filterStatus, setFilterStatus,
    filterCategory, setFilterCategory,
    filterSegment, setFilterSegment,
    filterDateFrom, setFilterDateFrom,
    filterDateTo, setFilterDateTo,
    filterBranch, setFilterBranch,
    clearFilters,
  };
}

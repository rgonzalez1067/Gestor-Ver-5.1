import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import api from '../utils/api';
import { INBOX_CHANGED } from '../utils/inboxEvents';

/**
 * Estado global de mensajes NO leídos en el Centro de Mensajes (bandeja).
 * - Consulta `/inbox/me/summary` (campo `unread` = notificaciones + conversaciones sin leer).
 * - Se refresca por: evento global `inbox:changed` (nuevo mensaje WS / lectura),
 *   polling corto (20s) y al recuperar foco de la pestaña.
 * - Alimenta el banner rojo global persistente.
 */
const UnreadMessagesContext = createContext({ unread: 0, loaded: false, alerts: { push: true, unread_banner: true }, refresh: () => {} });

export const useUnreadMessages = () => useContext(UnreadMessagesContext);

export const UnreadMessagesProvider = ({ children }) => {
  const [unread, setUnread] = useState(0);
  // `loaded` = ya se completó al menos una consulta al backend. Evita que el
  // banner trate el valor por defecto (0) como "sin mensajes confirmado".
  const [loaded, setLoaded] = useState(false);
  const [alerts, setAlerts] = useState({ push: true, unread_banner: true });
  const timerRef = useRef(null);

  const refresh = useCallback(async () => {
    const token = localStorage.getItem('session_token');
    if (!token) {
      setUnread(0);
      setLoaded(true);
      return;
    }
    try {
      const [{ data }, cfg] = await Promise.all([
        api.get('/inbox/me/summary'),
        api.get('/notifications/ui-alerts/me').catch(() => null),
      ]);
      setUnread(Number(data?.unread) || 0);
      if (cfg?.data) setAlerts({ push: cfg.data.push !== false, unread_banner: cfg.data.unread_banner !== false });
    } catch {
      /* silencioso: no bloquea la UI */
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    refresh();
    const onChanged = () => refresh();
    window.addEventListener(INBOX_CHANGED, onChanged);
    window.addEventListener('focus', onChanged);
    timerRef.current = setInterval(refresh, 20000);
    return () => {
      window.removeEventListener(INBOX_CHANGED, onChanged);
      window.removeEventListener('focus', onChanged);
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [refresh]);

  return (
    <UnreadMessagesContext.Provider value={{ unread, loaded, alerts, refresh }}>
      {children}
    </UnreadMessagesContext.Provider>
  );
};

export default UnreadMessagesProvider;

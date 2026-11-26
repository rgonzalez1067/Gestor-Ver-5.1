import { useEffect, useState, useCallback, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import api from '../../utils/api';
import { MessageSquare, Clock, ArrowRight, X } from 'lucide-react';

const POLL_MS = 30000;

// Alerta GLOBAL bidireccional (Generador e Implementador del proyecto): nuevo mensaje en el chat.
export default function ProjectChatAlert() {
  const [alerts, setAlerts] = useState([]);
  const navigate = useNavigate();
  const location = useLocation();
  const shown = useRef(new Set());
  const fetchAlerts = useCallback(() => {
    if (!localStorage.getItem('session_token') || document.visibilityState === 'hidden') return;
    api.get('/projects-chat/alerts').then(r => {
      const fresh = (r.data || []).filter(a => !shown.current.has(a.last_message.message_id));
      setAlerts(fresh);
    }).catch(() => {});
  }, []);
  useEffect(() => {
    fetchAlerts();
    const t = setInterval(fetchAlerts, POLL_MS);
    const onVis = () => document.visibilityState === 'visible' && fetchAlerts();
    document.addEventListener('visibilitychange', onVis);
    return () => { clearInterval(t); document.removeEventListener('visibilitychange', onVis); };
  }, [fetchAlerts]);
  useEffect(() => {
    if (location.pathname === '/login') setAlerts([]);
    else fetchAlerts();
  }, [location.pathname, fetchAlerts]);

  const close = async (a, goToChat) => {
    shown.current.add(a.last_message.message_id);
    setAlerts(list => list.filter(x => x.project_id !== a.project_id));
    if (goToChat) {
      navigate(`/projects?chat=${a.project_id}`);
    } else {
      api.post(`/projects-chat/alerts/${a.project_id}/dismiss`).catch(() => {});
    }
  };
  if (!alerts.length || location.pathname === '/login') return null;
  const a = alerts[0];
  return (
    <div className="fixed bottom-5 right-5 z-[60] w-[390px] rounded-xl border-2 border-orange-400 bg-white shadow-[0_12px_40px_-6px_rgba(234,88,12,0.55)] ring-4 ring-orange-200/70 overflow-hidden animate-in slide-in-from-bottom-4"
      role="alertdialog" data-testid="chat-alert">
      <div className="bg-gradient-to-r from-orange-500 via-rose-500 to-fuchsia-600 text-white px-4 py-3 flex items-center gap-2">
        <span className="relative flex h-7 w-7 items-center justify-center rounded-full bg-white/25">
          <span className="absolute inline-flex h-full w-full rounded-full bg-white/50 animate-ping" />
          <MessageSquare size={15} className="relative" />
        </span>
        <p className="text-sm font-bold flex-1 tracking-wide">¡Nuevo mensaje en tu proyecto!</p>
        {alerts.length > 1 && <span className="text-[11px] font-bold bg-yellow-300 text-rose-700 rounded-full px-2 py-0.5" data-testid="chat-alert-more">+{alerts.length - 1}</span>}
        <button onClick={() => close(a, false)} className="opacity-90 hover:opacity-100" title="Leer después" data-testid="chat-alert-close"><X size={16} /></button>
      </div>
      <div className="px-4 py-3 space-y-1.5 bg-orange-50">
        <p className="text-xs font-semibold text-slate-700" data-testid="chat-alert-project">
          <span className="font-mono text-orange-700">{a.project_number}</span> · {a.client_name}
          {a.unread > 1 && <span className="ml-1.5 rounded-full bg-rose-600 px-1.5 py-0.5 text-[10px] font-bold text-white">{a.unread} sin leer</span>}
        </p>
        <p className="text-xs font-bold text-rose-700">{a.last_message.user_name} <span className="font-normal text-slate-600">· {(a.last_message.roles || []).join(' / ')}</span></p>
        <p className="text-sm font-medium text-slate-900 line-clamp-3 whitespace-pre-wrap rounded-md border-l-4 border-orange-500 bg-white px-3 py-2 shadow-sm" data-testid="chat-alert-text">{a.last_message.text}</p>
      </div>
      <div className="px-4 py-3 flex justify-end gap-2 bg-orange-50 border-t border-orange-100">
        <button onClick={() => close(a, false)} className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md border border-orange-300 bg-white text-sm text-orange-700 hover:bg-orange-100" data-testid="chat-alert-later"><Clock size={14} /> Leer después</button>
        <button onClick={() => close(a, true)} className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md bg-gradient-to-r from-orange-500 to-rose-600 text-sm font-semibold text-white shadow hover:from-orange-600 hover:to-rose-700" data-testid="chat-alert-go"><ArrowRight size={14} /> Ir al Chat</button>
      </div>
    </div>
  );
}

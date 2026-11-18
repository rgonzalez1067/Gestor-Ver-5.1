import { useEffect, useState, useCallback, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import api from '../../utils/api';
import { MessageSquare, Clock, ArrowRight, X } from 'lucide-react';

const POLL_MS = 30000;

// Alerta GLOBAL para el Implementador: nuevo mensaje en el chat de uno de sus proyectos.
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
    <div className="fixed bottom-5 right-5 z-[60] w-[380px] rounded-xl border border-indigo-200 bg-white shadow-2xl overflow-hidden animate-in slide-in-from-bottom-4"
      role="alertdialog" data-testid="chat-alert">
      <div className="bg-indigo-600 text-white px-4 py-2.5 flex items-center gap-2">
        <MessageSquare size={16} />
        <p className="text-sm font-semibold flex-1">Nuevo mensaje en tu proyecto</p>
        {alerts.length > 1 && <span className="text-[11px] bg-white/20 rounded-full px-2" data-testid="chat-alert-more">+{alerts.length - 1}</span>}
        <button onClick={() => close(a, false)} className="opacity-80 hover:opacity-100" title="Leer después" data-testid="chat-alert-close"><X size={15} /></button>
      </div>
      <div className="px-4 py-3 space-y-1.5">
        <p className="text-xs text-slate-500" data-testid="chat-alert-project">{a.project_number} · {a.client_name}{a.unread > 1 ? ` · ${a.unread} sin leer` : ''}</p>
        <p className="text-xs font-semibold text-indigo-700">{a.last_message.user_name} <span className="font-normal text-slate-500">· {(a.last_message.roles || []).join(' / ')}</span></p>
        <p className="text-sm text-slate-800 line-clamp-3 whitespace-pre-wrap" data-testid="chat-alert-text">{a.last_message.text}</p>
      </div>
      <div className="px-4 pb-3 flex justify-end gap-2">
        <button onClick={() => close(a, false)} className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md border border-slate-300 text-sm text-slate-700 hover:bg-slate-50" data-testid="chat-alert-later"><Clock size={14} /> Leer después</button>
        <button onClick={() => close(a, true)} className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md bg-indigo-600 text-sm text-white hover:bg-indigo-700" data-testid="chat-alert-go"><ArrowRight size={14} /> Ir al Chat</button>
      </div>
    </div>
  );
}

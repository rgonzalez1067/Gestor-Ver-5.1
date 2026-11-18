import { useState, useEffect, useRef, useCallback } from 'react';
import { toast } from 'sonner';
import api from '../../utils/api';
import { Button } from '../ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '../ui/sheet';
import { MessageSquare, Send, Users, Eye, CheckCheck, Check } from 'lucide-react';

const ROLE_SHORT = { 'Generador': 'Gen', 'Gerente Comercial': 'Gte Com', 'Implementador': 'Impl', 'Coordinador de Implementación': 'Coord Impl', 'Gerente de Implementación': 'Gte Impl' };
const fmt = (iso) => new Date(iso).toLocaleString('es-VE', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });

// Botón de chat de la grilla con indicador de no leídos.
export const ProjectChatButton = ({ project, info, onOpen }) => {
  if (!info) return null;
  const unread = info.unread || 0;
  return (
    <Button size="sm" variant="outline" onClick={() => onOpen(project)} data-testid={`chat-btn-${project.project_id}`}
      title={unread ? `${unread} mensaje(s) sin leer` : info.access === 'ro' ? 'Chat del proyecto (solo lectura)' : 'Chat del proyecto'}
      className={`h-8 px-2 relative ${unread ? 'text-indigo-700 border-indigo-300 bg-indigo-50' : 'text-indigo-500 hover:bg-indigo-50'}`}>
      <MessageSquare size={14} />
      {unread > 0 && (
        <span className="absolute -top-1.5 -right-1.5 min-w-[16px] h-4 px-1 rounded-full bg-red-600 text-white text-[9px] font-bold flex items-center justify-center" data-testid={`chat-unread-${project.project_id}`}>
          {unread > 99 ? '99+' : unread}
        </span>
      )}
    </Button>
  );
};

const Bubble = ({ m, mine }) => (
  <div className={`flex ${mine ? 'justify-end' : 'justify-start'}`} data-testid={`chat-msg-${m.message_id}`}>
    <div className={`max-w-[82%] rounded-2xl px-3.5 py-2 shadow-sm ${mine ? 'bg-indigo-600 text-white rounded-br-sm' : 'bg-white border border-slate-200 text-slate-800 rounded-bl-sm'}`}>
      <p className={`text-[11px] font-semibold ${mine ? 'text-indigo-100' : 'text-indigo-700'}`}>
        {m.user_name} <span className="font-normal opacity-80">· {(m.roles || []).join(' / ')}</span>
      </p>
      <p className="text-sm whitespace-pre-wrap break-words mt-0.5">{m.text}</p>
      <p className={`text-[10px] mt-1 flex items-center gap-1 justify-end ${mine ? 'text-indigo-200' : 'text-slate-400'}`} title={m.read_by?.length ? `Leído por: ${m.read_by.join(', ')}` : 'Sin leer por otros participantes'}>
        {fmt(m.created_at)} {m.read_by?.length ? <><CheckCheck size={12} /> Leído ({m.read_by.length})</> : <><Check size={12} /> Enviado</>}
      </p>
    </div>
  </div>
);

// Panel lateral del chat operativo del proyecto.
export const ProjectChatDrawer = ({ project, onClose, currentUserId }) => {
  const [data, setData] = useState(null);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const endRef = useRef(null);
  const pid = project?.project_id;
  const load = useCallback(() => {
    if (!pid) return;
    api.get(`/projects/${pid}/chat`).then(r => setData(r.data)).catch(e => { toast.error(e.response?.data?.detail || 'No se pudo abrir el chat'); onClose(); });
  }, [pid, onClose]);
  useEffect(() => {
    setData(null); setText('');
    if (!pid) return undefined;
    load();
    const t = setInterval(() => document.visibilityState === 'visible' && load(), 8000);
    return () => clearInterval(t);
  }, [pid, load]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [data?.messages?.length]);
  const send = async () => {
    if (!text.trim()) return;
    setSending(true);
    try {
      const { data: m } = await api.post(`/projects/${pid}/chat`, { text });
      setData(d => ({ ...d, messages: [...d.messages, m] }));
      setText('');
    } catch (e) { toast.error(e.response?.data?.detail || 'No se pudo enviar'); }
    finally { setSending(false); }
  };
  return (
    <Sheet open={!!project} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-xl p-0 flex flex-col" data-testid="project-chat-drawer">
        <SheetHeader className="px-5 py-4 border-b bg-slate-900 text-white">
          <SheetTitle className="text-white flex items-center gap-2 text-base"><MessageSquare size={17} /> Chat Operativo: {project?.project_number || data?.project?.project_number}
            <span className="font-normal text-slate-300 truncate">| {project?.client_name || data?.project?.client_name}</span></SheetTitle>
          <p className="text-xs text-slate-300 flex items-start gap-1.5 mt-1" data-testid="chat-participants">
            <Users size={13} className="shrink-0 mt-0.5" />
            {(data?.participants || []).map(p => `${p.name} (${p.roles.map(r => ROLE_SHORT[r] || r).join('/')})`).join(', ') || 'Cargando participantes…'}
          </p>
        </SheetHeader>
        <div className="flex-1 overflow-y-auto bg-slate-50 px-4 py-4 space-y-3" data-testid="chat-messages">
          {data && data.messages.length === 0 && <p className="text-center text-sm text-slate-400 mt-10" data-testid="chat-empty">Aún no hay mensajes. Inicia la conversación del proyecto.</p>}
          {(data?.messages || []).map(m => <Bubble key={m.message_id} m={m} mine={m.user_id === currentUserId} />)}
          <div ref={endRef} />
        </div>
        {data?.can_write ? (
          <div className="border-t p-3 flex gap-2 bg-white">
            <textarea rows={2} value={text} onChange={(e) => setText(e.target.value)} maxLength={4000} data-testid="chat-input"
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder="Escriba su mensaje aquí… (Enter envía, Shift+Enter nueva línea)"
              className="flex-1 resize-none rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
            <Button onClick={send} disabled={sending || !text.trim()} className="bg-indigo-600 hover:bg-indigo-700 self-end" data-testid="chat-send-btn"><Send size={15} className="mr-1" />Enviar</Button>
          </div>
        ) : data && (
          <p className="border-t px-4 py-3 text-xs text-amber-700 bg-amber-50 flex items-center gap-1.5" data-testid="chat-readonly"><Eye size={13} /> Modo solo lectura (Administrador): no eres participante de este proyecto.</p>
        )}
      </SheetContent>
    </Sheet>
  );
};

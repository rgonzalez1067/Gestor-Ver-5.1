import { useState } from 'react';
import { Landmark } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const EntityLogo = ({ entity, testId }) => {
  const [failed, setFailed] = useState(false);
  const url = entity?.bank_logo_url;
  return (
    <span className="inline-flex items-center justify-center w-7 h-7 rounded-md bg-white border border-slate-200 shadow-sm overflow-hidden" data-testid={testId}>
      {url && !failed
        ? <img src={`${API_URL}${url}`} alt={entity.name} className="w-full h-full object-contain p-0.5" onError={() => setFailed(true)} />
        : <Landmark size={13} className="text-slate-500" />}
    </span>
  );
};

export const SponsorLogos = ({ quote, banksById }) => {
  const bank = banksById[quote.sponsoring_bank_id] || { name: quote.sponsoring_bank_name };
  const processor = quote.sponsoring_processor_id
    ? (banksById[quote.sponsoring_processor_id] || { name: quote.sponsoring_processor_name })
    : null;
  const label = [processor?.name || quote.sponsoring_processor_name, bank?.name || quote.sponsoring_bank_name].filter(Boolean).join(' — ');
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="inline-flex items-center gap-0.5 cursor-default" data-testid={`sponsored-badge-${quote.quote_id}`}
            aria-label={`Patrocinado por: ${label || 'no especificado'}`}>
            {processor && <EntityLogo entity={processor} testId={`sponsor-processor-logo-${quote.quote_id}`} />}
            <EntityLogo entity={bank} testId={`sponsor-bank-logo-${quote.quote_id}`} />
          </span>
        </TooltipTrigger>
        <TooltipContent side="top" data-testid={`sponsored-tooltip-${quote.quote_id}`}>
          <p className="text-xs">
            {processor ? `Procesador: ${processor.name || quote.sponsoring_processor_name} · ` : ''}Banco Patrocinante: {bank?.name || quote.sponsoring_bank_name || 'no especificado'}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};

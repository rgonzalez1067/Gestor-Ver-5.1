import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../../ui/dropdown-menu';
import { Button } from '../../ui/button';
import { Zap, ChevronDown, Trash2, Building2, Users, BarChart3, UserCog, Tag, Cog, Wrench } from 'lucide-react';
import { MASS_ACTIONS } from './MassActionDialog';

const ICONS = { delete: Trash2, group_brand: Building2, group: Building2, coord_impl: Users, segment: BarChart3, ejecutivo: UserCog, categoria: Tag, integrador: Cog, tipo_servicio: Wrench };

export const MassActionsMenu = ({ count, onPick, actions = MASS_ACTIONS }) => (
  <DropdownMenu>
    <DropdownMenuTrigger asChild>
      <Button size="sm" disabled={count === 0} className="bg-amber-500 hover:bg-amber-600 text-white" data-testid="mass-actions-btn">
        <Zap size={14} className="mr-1.5" /> Acciones Masivas ({count} seleccionados) <ChevronDown size={14} className="ml-1" />
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="start" className="w-72">
      {actions.map(a => {
        const Icon = ICONS[a.id];
        return (
          <DropdownMenuItem key={a.id} onSelect={() => onPick(a.id)} data-testid={`mass-action-${a.id}`}
            className={a.id === 'delete' ? 'text-red-600 focus:text-red-700' : ''}>
            <Icon size={14} className="mr-2" /> {a.label}
          </DropdownMenuItem>
        );
      })}
    </DropdownMenuContent>
  </DropdownMenu>
);

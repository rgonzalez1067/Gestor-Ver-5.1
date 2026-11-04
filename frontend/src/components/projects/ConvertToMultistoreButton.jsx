import React, { useState } from 'react';
import { Button } from '../ui/button';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '../ui/alert-dialog';
import { Plus, Store } from 'lucide-react';

export const ConvertToMultistoreButton = ({ onConfirm }) => {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button type="button" size="sm" variant="outline" onClick={() => setOpen(true)}
        className="mt-3 text-indigo-600 border-indigo-200 hover:bg-indigo-50" data-testid="master-single-add-branch">
        <Plus size={14} className="mr-1" /><Store size={13} className="mr-1" />Agregar Sucursal
      </Button>
      <AlertDialog open={open} onOpenChange={setOpen}>
        <AlertDialogContent data-testid="master-convert-confirm">
          <AlertDialogHeader>
            <AlertDialogTitle>¿Convertir el proyecto en multitienda?</AlertDialogTitle>
            <AlertDialogDescription>
              Este proyecto es de sede única. Al agregar sucursales pasará a ser multitienda: la sede actual quedará como
              la Sucursal 1 con todas sus cajas, medios de pago y avance de la matriz. Luego podrás repartir cajas a las
              nuevas sucursales. El cambio se aplica al pulsar "Guardar Override".
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="master-convert-cancel">Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={onConfirm} className="bg-indigo-600 hover:bg-indigo-700" data-testid="master-convert-accept">
              Sí, convertir
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};

import * as React from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { ConnectionWizard } from './connection-wizard';

export interface CreateConnectionWizardDialogProps {
  triggerLabel?: string;
  triggerVariant?: 'default' | 'outline' | 'secondary' | 'ghost' | 'destructive';
  onCreated?: () => void;
}

export function CreateConnectionWizardDialog({
  triggerLabel = 'Nueva conexión (Asistente)',
  triggerVariant = 'default',
  onCreated,
}: CreateConnectionWizardDialogProps) {
  const [open, setOpen] = React.useState(false);

  const handleComplete = () => {
    setOpen(false);
    onCreated?.();
  };

  const handleCancel = () => {
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant={triggerVariant}>{triggerLabel}</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Asistente de Conexión</DialogTitle>
          <DialogDescription>
            Crea una nueva conexión paso a paso con el asistente guiado
          </DialogDescription>
        </DialogHeader>

        <ConnectionWizard onComplete={handleComplete} onCancel={handleCancel} />
      </DialogContent>
    </Dialog>
  );
}

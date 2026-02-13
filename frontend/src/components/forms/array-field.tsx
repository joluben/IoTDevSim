import * as React from 'react';
import { Plus, Trash2, GripVertical } from 'lucide-react';
import { useFieldArray, Control, FieldValues, FieldPath } from 'react-hook-form';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { cn } from '@/lib/utils';

interface ArrayFieldProps<TFieldValues extends FieldValues> {
  control: Control<TFieldValues>;
  name: FieldPath<TFieldValues>;
  label: string;
  description?: string;
  fields: {
    name: string;
    label: string;
    placeholder?: string;
    type?: 'text' | 'number' | 'password';
  }[];
  defaultItem: Record<string, any>;
  minItems?: number;
  maxItems?: number;
  addButtonLabel?: string;
  emptyMessage?: string;
}

export function ArrayField<TFieldValues extends FieldValues>({
  control,
  name,
  label,
  description,
  fields,
  defaultItem,
  minItems = 0,
  maxItems = 10,
  addButtonLabel = 'Agregar',
  emptyMessage = 'No hay elementos. Haz clic en "Agregar" para crear uno.',
}: ArrayFieldProps<TFieldValues>) {
  const { fields: items, append, remove } = useFieldArray({
    control,
    name: name as any,
  });

  const canAdd = items.length < maxItems;
  const canRemove = items.length > minItems;

  return (
    <div className="space-y-4">
      <div>
        <Label className="text-base font-semibold">{label}</Label>
        {description && (
          <p className="text-sm text-muted-foreground mt-1">{description}</p>
        )}
      </div>

      {items.length === 0 ? (
        <div className="rounded-lg border border-dashed p-8 text-center">
          <p className="text-sm text-muted-foreground mb-4">{emptyMessage}</p>
          {canAdd && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => append(defaultItem as any)}
            >
              <Plus className="h-4 w-4 mr-2" />
              {addButtonLabel}
            </Button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item, index) => (
            <div
              key={item.id}
              className="relative rounded-lg border p-4 space-y-3 bg-card"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <GripVertical className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">
                    Elemento {index + 1}
                  </span>
                </div>
                {canRemove && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => remove(index)}
                    className="h-8 w-8"
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                    <span className="sr-only">Eliminar</span>
                  </Button>
                )}
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                {fields.map((field) => (
                  <FormField
                    key={field.name}
                    control={control}
                    name={`${name}.${index}.${field.name}` as FieldPath<TFieldValues>}
                    render={({ field: formField }) => (
                      <FormItem>
                        <FormLabel>{field.label}</FormLabel>
                        <FormControl>
                          <Input
                            {...formField}
                            type={field.type || 'text'}
                            placeholder={field.placeholder}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                ))}
              </div>
            </div>
          ))}

          {canAdd && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => append(defaultItem as any)}
              className="w-full"
            >
              <Plus className="h-4 w-4 mr-2" />
              {addButtonLabel}
            </Button>
          )}
        </div>
      )}

      {!canAdd && items.length >= maxItems && (
        <p className="text-xs text-muted-foreground">
          Máximo de {maxItems} elementos alcanzado
        </p>
      )}
    </div>
  );
}

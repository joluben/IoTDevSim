import * as React from 'react';
import type {
  FieldValues,
  UseFormReturn,
  FieldPath,
  SubmitHandler,
  PathValue,
} from 'react-hook-form';
import { useWatch } from 'react-hook-form';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';

export type DynamicFieldType =
  | 'text'
  | 'textarea'
  | 'number'
  | 'password'
  | 'switch'
  | 'select'
  | 'text_array';

export interface SelectOption {
  label: string;
  value: string;
  disabled?: boolean;
}

export interface VisibilityRule<TValues extends FieldValues> {
  field: string;
  equals?: unknown;
  notEquals?: unknown;
  includes?: string;
}

export interface DynamicFormFieldConfig<TValues extends FieldValues> {
  name: FieldPath<TValues>;
  label: string;
  type: DynamicFieldType;
  placeholder?: string;
  description?: string;
  disabled?: boolean;
  options?: SelectOption[];
  visibleWhen?: Array<VisibilityRule<TValues>>;
  layout?: 'full' | 'half';
}

export interface DynamicFormProps<TValues extends FieldValues> {
  form: UseFormReturn<TValues>;
  fields: Array<DynamicFormFieldConfig<TValues>>;
  onSubmit: SubmitHandler<TValues>;
  submitLabel?: string;
  isSubmitting?: boolean;
  className?: string;
  footer?: React.ReactNode;
}

function evaluateVisibility<TValues extends FieldValues>(
  rules: Array<VisibilityRule<TValues>> | undefined,
  values: TValues
) {
  if (!rules || rules.length === 0) return true;

  const getValueAtPath = (obj: unknown, path: string): unknown => {
    if (!path) return undefined;

    return path.split('.').reduce<unknown>((acc, key) => {
      if (acc === null || acc === undefined) return undefined;
      if (typeof acc !== 'object') return undefined;
      return (acc as Record<string, unknown>)[key];
    }, obj);
  };

  return rules.every((rule) => {
    const current = getValueAtPath(values, rule.field);

    if (rule.equals !== undefined) return current === rule.equals;
    if (rule.notEquals !== undefined) return current !== rule.notEquals;

    if (rule.includes !== undefined) {
      return typeof current === 'string' && current.includes(rule.includes);
    }

    return true;
  });
}

function renderSelectValueLabel(options: SelectOption[] | undefined, value: unknown) {
  if (!options) return value ? String(value) : '';
  const match = options.find((o) => o.value === String(value));
  return match ? match.label : value ? String(value) : '';
}

function normalizeTextArray(value: unknown): string {
  if (Array.isArray(value) && value.every((v) => typeof v === 'string')) {
    return value.join(', ');
  }
  return typeof value === 'string' ? value : '';
}

function parseTextArray(text: string): string[] {
  return text
    .split(',')
    .map((v) => v.trim())
    .filter((v) => v.length > 0);
}

export function DynamicForm<TValues extends FieldValues>({
  form,
  fields,
  onSubmit,
  submitLabel = 'Save',
  isSubmitting = false,
  className,
  footer,
}: DynamicFormProps<TValues>) {
  const values = useWatch({ control: form.control }) as TValues;

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className={className}>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {fields.map((fieldConfig) => {
            const isVisible = evaluateVisibility(fieldConfig.visibleWhen, values);
            if (!isVisible) return null;

            const layout = fieldConfig.layout ?? 'full';
            const wrapperClassName = layout === 'half' ? 'md:col-span-1' : 'md:col-span-2';

            return (
              <div key={String(fieldConfig.name)} className={wrapperClassName}>
                <FormField
                  control={form.control}
                  name={fieldConfig.name as unknown as never}
                  render={({ field }) => {
                    const disabled = fieldConfig.disabled || isSubmitting;

                    if (fieldConfig.type === 'switch') {
                      return (
                        <FormItem className="flex items-center justify-between rounded-md border p-3">
                          <div className="space-y-0.5">
                            <FormLabel>{fieldConfig.label}</FormLabel>
                            {fieldConfig.description && (
                              <FormDescription>{fieldConfig.description}</FormDescription>
                            )}
                          </div>
                          <FormControl>
                            <Switch
                              checked={Boolean(field.value)}
                              onCheckedChange={(checked) => field.onChange(checked)}
                              disabled={disabled}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      );
                    }

                    if (fieldConfig.type === 'select') {
                      const currentLabel = renderSelectValueLabel(fieldConfig.options, field.value);

                      return (
                        <FormItem>
                          <FormLabel>{fieldConfig.label}</FormLabel>
                          <FormControl>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button
                                  type="button"
                                  variant="outline"
                                  className="w-full justify-between"
                                  disabled={disabled}
                                >
                                  <span className="truncate">
                                    {currentLabel || fieldConfig.placeholder || 'Select'}
                                  </span>
                                  <span className="text-muted-foreground">▾</span>
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="start" className="w-64">
                                {(fieldConfig.options ?? []).map((opt) => (
                                  <DropdownMenuItem
                                    key={opt.value}
                                    disabled={opt.disabled}
                                    onSelect={() => field.onChange(opt.value)}
                                  >
                                    {opt.label}
                                  </DropdownMenuItem>
                                ))}
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </FormControl>
                          {fieldConfig.description && (
                            <FormDescription>{fieldConfig.description}</FormDescription>
                          )}
                          <FormMessage />
                        </FormItem>
                      );
                    }

                    if (fieldConfig.type === 'textarea') {
                      return (
                        <FormItem>
                          <FormLabel>{fieldConfig.label}</FormLabel>
                          <FormControl>
                            <Textarea
                              placeholder={fieldConfig.placeholder}
                              disabled={disabled}
                              {...field}
                            />
                          </FormControl>
                          {fieldConfig.description && (
                            <FormDescription>{fieldConfig.description}</FormDescription>
                          )}
                          <FormMessage />
                        </FormItem>
                      );
                    }

                    if (fieldConfig.type === 'text_array') {
                      return (
                        <FormItem>
                          <FormLabel>{fieldConfig.label}</FormLabel>
                          <FormControl>
                            <Input
                              type="text"
                              placeholder={fieldConfig.placeholder}
                              disabled={disabled}
                              value={normalizeTextArray(field.value)}
                              onChange={(e) => {
                                const parsed = parseTextArray(e.target.value);
                                const nextValue = parsed as PathValue<TValues, FieldPath<TValues>>;
                                field.onChange(nextValue);
                              }}
                            />
                          </FormControl>
                          {fieldConfig.description && (
                            <FormDescription>{fieldConfig.description}</FormDescription>
                          )}
                          <FormMessage />
                        </FormItem>
                      );
                    }

                    const inputType: React.HTMLInputTypeAttribute =
                      fieldConfig.type === 'password'
                        ? 'password'
                        : fieldConfig.type === 'number'
                          ? 'number'
                          : 'text';

                    return (
                      <FormItem>
                        <FormLabel>{fieldConfig.label}</FormLabel>
                        <FormControl>
                          <Input
                            type={inputType}
                            placeholder={fieldConfig.placeholder}
                            disabled={disabled}
                            value={field.value ?? ''}
                            onChange={(e) => {
                              if (fieldConfig.type === 'number') {
                                const next = e.target.value;
                                field.onChange(next === '' ? undefined : Number(next));
                                return;
                              }

                              field.onChange(e);
                            }}
                            onBlur={field.onBlur}
                            name={field.name}
                            ref={field.ref}
                          />
                        </FormControl>
                        {fieldConfig.description && (
                          <FormDescription>{fieldConfig.description}</FormDescription>
                        )}
                        <FormMessage />
                      </FormItem>
                    );
                  }}
                />
              </div>
            );
          })}
        </div>

        {footer ? (
          footer
        ) : (
          <div className="mt-6 flex justify-end">
            <Button type="submit" disabled={isSubmitting}>
              {submitLabel}
            </Button>
          </div>
        )}
      </form>
    </Form>
  );
}

import * as React from 'react';
import { AlertCircle, CheckCircle2, Info } from 'lucide-react';
import { Control, FieldPath, FieldValues } from 'react-hook-form';
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { cn } from '@/lib/utils';

interface ValidatedFieldProps<TFieldValues extends FieldValues> {
  control: Control<TFieldValues>;
  name: FieldPath<TFieldValues>;
  label: string;
  description?: string;
  placeholder?: string;
  type?: 'text' | 'number' | 'password' | 'email' | 'url' | 'textarea' | 'select';
  options?: { value: string; label: string }[];
  helpText?: string;
  successMessage?: string;
  errorRecovery?: string;
  required?: boolean;
  disabled?: boolean;
  className?: string;
}

export function ValidatedField<TFieldValues extends FieldValues>({
  control,
  name,
  label,
  description,
  placeholder,
  type = 'text',
  options = [],
  helpText,
  successMessage,
  errorRecovery,
  required = false,
  disabled = false,
  className,
}: ValidatedFieldProps<TFieldValues>) {
  return (
    <FormField
      control={control}
      name={name}
      render={({ field, fieldState }) => {
        const hasError = !!fieldState.error;
        const isValid = fieldState.isDirty && !hasError;

        return (
          <FormItem className={className}>
            <FormLabel>
              {label}
              {required && <span className="text-destructive ml-1">*</span>}
            </FormLabel>
            <FormControl>
              <div className="relative">
                {type === 'textarea' ? (
                  <Textarea
                    {...field}
                    placeholder={placeholder}
                    disabled={disabled}
                    className={cn(
                      hasError && 'border-destructive focus-visible:ring-destructive',
                      isValid && 'border-green-500 focus-visible:ring-green-500'
                    )}
                  />
                ) : type === 'select' ? (
                  <Select
                    onValueChange={field.onChange}
                    defaultValue={field.value}
                    disabled={disabled}
                  >
                    <SelectTrigger
                      className={cn(
                        hasError && 'border-destructive focus-visible:ring-destructive',
                        isValid && 'border-green-500 focus-visible:ring-green-500'
                      )}
                    >
                      <SelectValue placeholder={placeholder} />
                    </SelectTrigger>
                    <SelectContent>
                      {options.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Input
                    {...field}
                    type={type}
                    placeholder={placeholder}
                    disabled={disabled}
                    className={cn(
                      hasError && 'border-destructive focus-visible:ring-destructive',
                      isValid && 'border-green-500 focus-visible:ring-green-500'
                    )}
                  />
                )}
                {isValid && successMessage && (
                  <CheckCircle2 className="absolute right-3 top-3 h-4 w-4 text-green-500" />
                )}
                {hasError && (
                  <AlertCircle className="absolute right-3 top-3 h-4 w-4 text-destructive" />
                )}
              </div>
            </FormControl>

            {description && <FormDescription>{description}</FormDescription>}

            {helpText && !hasError && (
              <Alert className="mt-2">
                <Info className="h-4 w-4" />
                <AlertDescription className="text-xs">{helpText}</AlertDescription>
              </Alert>
            )}

            <FormMessage />

            {hasError && errorRecovery && (
              <Alert variant="destructive" className="mt-2">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle className="text-sm font-medium">Cómo resolver</AlertTitle>
                <AlertDescription className="text-xs mt-1">
                  {errorRecovery}
                </AlertDescription>
              </Alert>
            )}

            {isValid && successMessage && (
              <p className="text-xs text-green-600 dark:text-green-500 mt-1 flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" />
                {successMessage}
              </p>
            )}
          </FormItem>
        );
      }}
    />
  );
}

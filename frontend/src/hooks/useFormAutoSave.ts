import * as React from 'react';
import type { FieldValues, UseFormReturn } from 'react-hook-form';

interface UseFormAutoSaveOptions<TValues extends FieldValues> {
  enabled?: boolean;
  debounceMs?: number;
  storageKey?: string;
  onSave?: (values: TValues) => void | Promise<void>;
}

export function useFormAutoSave<TValues extends FieldValues>(
  form: UseFormReturn<TValues>,
  options: UseFormAutoSaveOptions<TValues>
) {
  const {
    enabled = false,
    debounceMs = 800,
    storageKey,
    onSave,
  } = options;

  const isHydratedRef = React.useRef(false);
  const timerRef = React.useRef<number | null>(null);

  React.useEffect(() => {
    if (!enabled || !storageKey) return;

    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) {
        isHydratedRef.current = true;
        return;
      }

      const parsed = JSON.parse(raw) as unknown;
      if (typeof parsed === 'object' && parsed) {
        form.reset(parsed as TValues);
      }
    } catch {
      // ignore
    } finally {
      isHydratedRef.current = true;
    }
  }, [enabled, storageKey, form]);

  React.useEffect(() => {
    if (!enabled) return;

    const subscription = form.watch((values) => {
      if (!isHydratedRef.current) return;

      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
      }

      timerRef.current = window.setTimeout(() => {
        if (storageKey) {
          try {
            localStorage.setItem(storageKey, JSON.stringify(values));
          } catch {
            // ignore
          }
        }

        if (onSave) {
          void onSave(values as TValues);
        }
      }, debounceMs);
    });

    return () => {
      subscription.unsubscribe();
      if (timerRef.current) window.clearTimeout(timerRef.current);
    };
  }, [enabled, debounceMs, storageKey, onSave, form]);

  const clearSavedDraft = React.useCallback(() => {
    if (!storageKey) return;
    try {
      localStorage.removeItem(storageKey);
    } catch {
      // ignore
    }
  }, [storageKey]);

  return { clearSavedDraft };
}

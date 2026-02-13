import { useState } from 'react';

export function useFormValidation<T extends object>(initial: T) {
  const [values, setValues] = useState<T>(initial);
  const [errors, setErrors] = useState<Record<string, string>>({});

  return { values, setValues, errors, setErrors };
}

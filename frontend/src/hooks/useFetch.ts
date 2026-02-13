import { useEffect, useState } from 'react';

export function useFetch<T>(factory: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const result = await factory();
        if (mounted) setData(result);
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [factory]);

  return { data, error, loading };
}

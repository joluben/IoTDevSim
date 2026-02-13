/**
 * SafeHtml Component
 * Renders sanitized HTML using DOMPurify to prevent XSS
 * Prefer using plain JSX; only use this when rendering trusted HTML is necessary.
 */

import * as React from 'react';
import { sanitizeHtml } from '@/utils/security';

export interface SafeHtmlProps {
  html: string;
  className?: string;
  // Optional: additional allowlist transformer if needed per feature
  transform?: (sanitized: string) => string;
}

export function SafeHtml({ html, className, transform }: SafeHtmlProps) {
  const sanitized = React.useMemo(() => {
    const clean = sanitizeHtml(html || '');
    return transform ? transform(clean) : clean;
  }, [html, transform]);

  return (
    <div
      className={className}
      // We are explicitly allowing this here as the HTML is sanitized.
      dangerouslySetInnerHTML={{ __html: sanitized }}
      aria-live="polite"
    />
  );
}

export default SafeHtml;

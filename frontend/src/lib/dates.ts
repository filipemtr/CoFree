/**
 * FastAPI serializes our database's UTC timestamps without a timezone suffix.
 * JavaScript interprets timezone-less ISO timestamps as *local* time, which
 * causes a 3-hour shift for users in UTC-3 (for example, Recife).
 *
 * Only ISO timestamps without an explicit offset are normalized. Explicit
 * offsets and Z timestamps (including browser-created Vault records) must be
 * preserved as-is. The browser then displays the instant in its local zone.
 */
const NAIVE_ISO_TIMESTAMP = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?$/;

export function parseApiTimestamp(value: string): Date {
  const timestamp = value.trim();
  return new Date(NAIVE_ISO_TIMESTAMP.test(timestamp) ? `${timestamp}Z` : timestamp);
}

export function formatDateTime(value?: string | null): string {
  if (!value) return 'Ainda não verificado';

  const date = parseApiTimestamp(value);
  if (!Number.isFinite(date.getTime())) return 'Data indisponível';

  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

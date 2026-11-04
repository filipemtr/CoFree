import assert from 'node:assert/strict';
import test from 'node:test';
import { parseApiTimestamp, formatDateTime } from '../src/lib/dates.ts';

test('interprets UTC timestamps without explicit offset as UTC', () => {
  assert.equal(
    parseApiTimestamp('2026-11-04T16:59:00').toISOString(),
    '2026-11-04T16:59:00.000Z'
  );
  assert.equal(
    parseApiTimestamp('2026-11-04T16:59:00.123456').toISOString(),
    '2026-11-04T16:59:00.123Z'
  );
});

test('preserves timestamps carrying explicit UTC or timezone offsets', () => {
  assert.equal(
    parseApiTimestamp('2026-11-04T16:59:00Z').toISOString(),
    '2026-11-04T16:59:00.000Z'
  );
  assert.equal(
    parseApiTimestamp('2026-11-04T13:59:00-03:00').toISOString(),
    '2026-11-04T16:59:00.000Z'
  );
});

test('shows 13:59 in America/Recife for an API timestamp of 16:59 UTC', () => {
  const previousTZ = process.env.TZ;
  try {
    process.env.TZ = 'America/Recife';
    assert.match(formatDateTime('2026-11-04T16:59:00'), /13:59/);
    assert.match(formatDateTime('2026-11-04T16:59:00Z'), /13:59/);
    assert.match(formatDateTime('2026-11-04T13:59:00-03:00'), /13:59/);
  } finally {
    if (previousTZ === undefined) delete process.env.TZ;
    else process.env.TZ = previousTZ;
  }
});

test('handles missing or invalid timestamps without crashing the interface', () => {
  assert.equal(formatDateTime(null), 'Ainda não verificado');
  assert.equal(formatDateTime(''), 'Ainda não verificado');
  assert.equal(formatDateTime('invalid'), 'Data indisponível');
});

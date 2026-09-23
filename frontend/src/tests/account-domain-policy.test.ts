import { describe, expect, it } from 'vitest';
import { isSzabistIslamabadEmail } from '../features/dashboard/utils';

describe('SZABIST Islamabad account policy', () => {
  it.each([
    'student@szabist-isb.pk',
    '2380223@szabist-isb.pk',
    '  FACULTY.MEMBER@SZABIST-ISB.PK  ',
  ])('accepts a valid institutional address: %s', (email) => {
    expect(isSzabistIslamabadEmail(email)).toBe(true);
  });

  it.each([
    'student@gmail.com',
    'student@szabist.edu.pk',
    'student@subdomain.szabist-isb.pk',
    'student@szabist-isb.pk.example.com',
    '@szabist-isb.pk',
    '',
    null,
    undefined,
  ])('rejects a non-institutional or missing address: %s', (email) => {
    expect(isSzabistIslamabadEmail(email)).toBe(false);
  });
});

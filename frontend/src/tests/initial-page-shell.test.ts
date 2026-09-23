import { describe, expect, it } from 'vitest';
import pageSource from '../../index.html?raw';

const rootMarkup = pageSource.match(/<div id="root">([\s\S]*?)<\/div>\s*<\/div>/)?.[0] || '';

describe('initial page shell', () => {
  it('shows a styled loader instead of exposing SEO copy before React starts', () => {
    expect(rootMarkup).toContain('classwire-boot');
    expect(rootMarkup).toContain('classwire-boot__indicator');
    expect(rootMarkup).not.toContain('SZABIST timetable and class schedule search');
  });

  it('retains SZABIST discovery metadata outside the transient app root', () => {
    expect(pageSource).toContain('SZABIST Islamabad timetables');
    expect(pageSource).toContain('application/ld+json');
    expect(pageSource).toContain('<noscript>');
  });
});

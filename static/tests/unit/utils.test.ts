import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getErrorMessage, isSafeCommand, formatDate, getElement } from '../../ts/foamflask_frontend';

describe('Frontend Utils', () => {
  describe('getErrorMessage', () => {
    it('should return message from Error object', () => {
      const error = new Error('Test error');
      expect(getErrorMessage(error)).toBe('Test error');
    });

    it('should return string error as is', () => {
      expect(getErrorMessage('String error')).toBe('String error');
    });

    it('should return "Unknown error" for non-error objects', () => {
      expect(getErrorMessage({ custom: 'obj' })).toBe('Unknown error');
    });
  });

  describe('isSafeCommand', () => {
    it('should return true for safe commands', () => {
      expect(isSafeCommand('ls')).toBe(true);
      expect(isSafeCommand('echo hello')).toBe(true);
      expect(isSafeCommand('blockMesh')).toBe(true);
    });

    it('should return false for commands with dangerous characters', () => {
      expect(isSafeCommand('ls; rm -rf /')).toBe(false);
      expect(isSafeCommand('cat file | grep text')).toBe(false);
      expect(isSafeCommand('echo $HOME')).toBe(false);
      expect(isSafeCommand('command &')).toBe(false);
    });
  });

  describe('formatDate', () => {
    it('should format timestamp to locale string', () => {
      const timestamp = 1609459200000; // 2021-01-01 00:00:00 UTC
      const formatted = formatDate(timestamp);
      // Validating exact string is hard due to locale differences in test env,
      // so we check it returns a string and contains the year.
      expect(typeof formatted).toBe('string');
      expect(formatted).toContain('2021');
    });
  });

  describe('getElement', () => {
    beforeEach(() => {
        document.body.innerHTML = `
            <div id="test-div">Content</div>
            <button id="test-btn">Click me</button>
        `;
    });

    it('should return existing element', () => {
        const el = getElement<HTMLDivElement>('test-div');
        expect(el).not.toBeNull();
        expect(el?.textContent).toBe('Content');
    });

    it('should return null for non-existing element', () => {
        const el = getElement('non-existent');
        expect(el).toBeNull();
    });
  });
});

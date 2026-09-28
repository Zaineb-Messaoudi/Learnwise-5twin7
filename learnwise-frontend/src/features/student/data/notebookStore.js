import { notebooks as seedNotebooks } from './notebooks';

const STORAGE_KEY = 'learnwise:notebooks';
export function getNotebooks() { try { const saved = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || 'null'); return Array.isArray(saved) ? saved : seedNotebooks; } catch { return seedNotebooks; } }
export function saveNotebooks(value) { window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value)); return value; }
export function createNotebook() { const next = { ...seedNotebooks[0], id: `notebook-${Date.now()}`, title: 'Untitled learning notebook', updated: 'Created just now', sources: 0, sourceItems: [] }; return saveNotebooks([next, ...getNotebooks()]); }

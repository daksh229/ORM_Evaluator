/**
 * Typed client for the OMR engine, talking through the Node bridge at /api.
 * Type names mirror omr_engine/models.py exactly so the wire format is
 * obvious in both directions.
 */

const API_BASE = '/api';

export interface SessionMeta {
  id: string;
  name: string;
  template_id: string;
  answer_key_id: string | null;
  created_at: string;
  sheet_count: number;
}

export interface BoxResult {
  question_id: number;
  option: string;
  status: 'marked' | 'blank' | 'ambiguous';
  score: number;
  source: 'cv' | 'claude';
  reason: string | null;
}

export interface ProcessResult {
  template_id: string;
  student_id: string | null;
  boxes: BoxResult[];
  warnings: string[];
}

export interface ScoredQuestion {
  question_id: number;
  expected: string[];
  selected: string[];
  is_correct: boolean;
  is_partial: boolean;
  points_earned: number;
  points_possible: number;
  has_ambiguous: boolean;
}

export interface ScoreReport {
  total_points: number;
  points_possible: number;
  percentage: number;
  correct_count: number;
  wrong_count: number;
  partial_count: number;
  wrong_question_ids: number[];
  ambiguous_question_ids: number[];
  questions: ScoredQuestion[];
}

export interface SheetResult {
  sheet_id: string;
  session_id: string;
  student_id: string | null;
  student_name: string | null;
  process_result: ProcessResult;
  score: ScoreReport | null;
  created_at: string;
}

export interface SessionDetail {
  meta: SessionMeta;
  sheets: SheetResult[];
}

export async function listTemplates(): Promise<string[]> {
  const r = await fetch(`${API_BASE}/templates`);
  const data = await jsonOrThrow<{ templates: string[] }>(r);
  return data.templates;
}

export function templatePdfUrl(id: string): string {
  return `${API_BASE}/templates/${encodeURIComponent(id)}/pdf`;
}

async function jsonOrThrow<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const text = await r.text().catch(() => '');
    throw new Error(`${r.status} ${r.statusText}: ${text}`);
  }
  return r.json() as Promise<T>;
}

export async function listSessions(): Promise<SessionMeta[]> {
  const r = await fetch(`${API_BASE}/sessions`);
  const data = await jsonOrThrow<{ sessions: SessionMeta[] }>(r);
  return data.sessions;
}

export async function getSession(id: string): Promise<SessionDetail> {
  const r = await fetch(`${API_BASE}/sessions/${encodeURIComponent(id)}`);
  return jsonOrThrow<SessionDetail>(r);
}

export async function createSession(opts: {
  name: string;
  template_id: string;
  answer_key_id?: string | null;
}): Promise<SessionMeta> {
  const fd = new FormData();
  fd.append('name', opts.name);
  fd.append('template_id', opts.template_id);
  if (opts.answer_key_id) fd.append('answer_key_id', opts.answer_key_id);
  const r = await fetch(`${API_BASE}/sessions`, { method: 'POST', body: fd });
  return jsonOrThrow<SessionMeta>(r);
}

export async function addScanToSession(
  sessionId: string,
  file: File,
  studentName?: string,
): Promise<SheetResult> {
  const fd = new FormData();
  fd.append('file', file);
  if (studentName) fd.append('student_name', studentName);
  const r = await fetch(
    `${API_BASE}/sessions/${encodeURIComponent(sessionId)}/scans`,
    { method: 'POST', body: fd },
  );
  return jsonOrThrow<SheetResult>(r);
}

export function exportCsvUrl(sessionId: string): string {
  return `${API_BASE}/sessions/${encodeURIComponent(sessionId)}/export.csv`;
}

export function exportXlsxUrl(sessionId: string): string {
  return `${API_BASE}/sessions/${encodeURIComponent(sessionId)}/export.xlsx`;
}

export async function overrideBox(
  sessionId: string,
  sheetId: string,
  boxIndex: number,
  status: 'marked' | 'blank' | 'ambiguous',
): Promise<SheetResult> {
  const r = await fetch(
    `${API_BASE}/sessions/${encodeURIComponent(sessionId)}/sheets/${encodeURIComponent(sheetId)}/boxes/${boxIndex}?status=${status}`,
    { method: 'PATCH' },
  );
  return jsonOrThrow<SheetResult>(r);
}

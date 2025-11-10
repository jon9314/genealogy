import axios from "axios";

import {
  Family,
  FamilyWithChildren,
  LineValidation,
  PageText,
  ParsePreview,
  Person,
  ReparentRequest,
  Source,
  UpdatePersonPayload,
  ValidationWarning,
} from "./types";

const client = axios.create({
  baseURL: "/api",
});

export async function listSources(): Promise<Source[]> {
  const { data } = await client.get<Source[]>("/files");
  return data;
}

export async function uploadFiles(files: File[]): Promise<Source[]> {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  const { data } = await client.post<Source[]>("/files/upload", form);
  return data;
}

export async function deleteSource(id: number): Promise<void> {
  await client.delete(`/files/${id}`);
}

export async function runOCR(sourceId: number): Promise<{ job_id: string }> {
  const { data } = await client.post(`/ocr/${sourceId}`);
  return data;
}

export async function getOCRProgress(jobId: string): Promise<{
  status: string;
  progress: { percent: number; current_page: number; total_pages: number };
  error: { message: string; suggestion: string };
}> {
  const { data } = await client.get(`/ocr/${jobId}/progress`);
  return data;
}

export async function getOCRStatus(
  sourceId: number,
  jobId: string,
  includeConfidence: boolean = false
): Promise<{ pages: number; ocr_done: boolean }> {
  const { data } = await client.get(`/ocr/${sourceId}/status`, {
    params: { job_id: jobId, include_confidence: includeConfidence },
  });
  return data;
}

export async function getOCRText(sourceId: number): Promise<PageText[]> {
  const { data } = await client.get<PageText[]>(`/ocr/${sourceId}/text`);
  return data;
}

export async function updateOCRText(sourceId: number, pageId: number, text: string): Promise<void> {
  await client.put(`/ocr/${sourceId}/text/${pageId}`, { text });
}

export async function validateOCRText(sourceId: number, text: string): Promise<LineValidation[]> {
  const { data } = await client.post<LineValidation[]>(`/ocr/${sourceId}/validate`, { text });
  return data;
}

export async function parseSourcePreview(sourceId: number): Promise<ParsePreview> {
  const { data } = await client.post(`/parse/${sourceId}/preview`);
  return data;
}

export async function parseSource(sourceId: number, page_indexes?: number[]): Promise<{ job_id: string }> {
  const { data } = await client.post(`/parse/${sourceId}`, { page_indexes });
  return data;
}

export async function getParseProgress(jobId: string): Promise<{
  status: string;
  progress: { current: number; total: number };
  stats: { people: number; families: number; children: number; flagged_lines: string[] };
  error: string;
}> {
  const { data } = await client.get(`/parse/${jobId}/progress`);
  return data;
}

export async function listPersons(params: { source_id?: number; gen?: number; q?: string } = {}): Promise<Person[]> {
  const { data } = await client.get<Person[]>("/persons", { params });
  return data;
}

export async function updatePerson(id: number, payload: UpdatePersonPayload): Promise<Person> {
  const { data } = await client.patch<Person>(`/persons/${id}`, payload);
  return data;
}

export async function deletePerson(id: number): Promise<void> {
  await client.delete(`/persons/${id}`);
}

export async function bulkUpdatePersons(personIds: number[], updates: Partial<UpdatePersonPayload>): Promise<{ count: number }> {
  const { data } = await client.post("/persons/bulk-update", {
    person_ids: personIds,
    updates,
  });
  return data;
}

export async function searchPersons(query: string): Promise<Person[]> {
  const { data } = await client.get<Person[]>("/persons/search", {
    params: { q: query },
  });
  return data;
}

export interface PersonFilters {
  missing_birth?: boolean;
  missing_death?: boolean;
  has_approx?: boolean;
  surname?: string;
  min_gen?: number;
  max_gen?: number;
  birth_year_min?: number;
  birth_year_max?: number;
  sex?: "M" | "F";
}

export async function filterPersons(filters: PersonFilters): Promise<Person[]> {
  const { data } = await client.get<Person[]>("/persons/filter", {
    params: filters,
  });
  return data;
}

export async function bulkDeletePersons(personIds: number[], keepPersonId?: number): Promise<{ count: number; kept_id?: number }> {
  const { data } = await client.post("/persons/bulk-delete", {
    person_ids: personIds,
    keep_person_id: keepPersonId,
  });
  return data;
}

export async function listFamilies(): Promise<FamilyWithChildren[]> {
  const { data } = await client.get<FamilyWithChildren[]>("/families");
  return data;
}

export async function updateFamily(id: number, payload: Partial<Family>): Promise<Family> {
  const { data } = await client.patch<Family>(`/families/${id}`, payload);
  return data;
}

export async function reparent(request: ReparentRequest): Promise<void> {
  await client.post("/families/reparent", request);
}

export async function exportGedcom(): Promise<Blob> {
  const { data } = await client.post(`/export/gedcom`, undefined, { responseType: "blob" });
  return data;
}

export async function exportCsv(): Promise<Blob> {
  const { data } = await client.post(`/export/csv`, undefined, { responseType: "blob" });
  return data;
}

export async function saveProject(filename?: string): Promise<string> {
  const { data } = await client.post<{ status: string; filename: string }>("/project/save", filename ? { filename } : {});
  return data.filename;
}

export async function autosaveProject(): Promise<string> {
  const { data } = await client.post<{ status: string; filename: string }>("/project/autosave");
  return data.filename;
}

export async function openProject(filename: string): Promise<void> {
  await client.post("/project/open", { filename });
}

export interface Backup {
  filename: string;
  timestamp: string;
  size_bytes: number;
  is_autosave: boolean;
}

export async function listBackups(): Promise<Backup[]> {
  const { data } = await client.get<{ backups: Backup[] }>("/project/backups");
  return data.backups;
}

export async function restoreBackup(filename: string): Promise<void> {
  await client.post("/project/restore", { filename });
}

export async function getValidationWarnings(): Promise<ValidationWarning[]> {
  const { data } = await client.get<ValidationWarning[]>("/validation/warnings");
  return data;
}

export async function getRelationshipValidation(): Promise<{
  orphans: Array<{ id: number; name: string; gen: number; birth: string | null; death: string | null; surname: string | null }>;
  orphan_count: number;
  total_people: number;
  connected_people: number;
  issues: Array<{ type: string; severity: string; message: string; person_ids: number[]; family_id: number | null }>;
  issue_count: number;
}> {
  const { data } = await client.get("/validation/relationships");
  return data;
}

export async function getNotifications(): Promise<
  { id: string; message: string; type: "success" | "error" }[]
> {
  const { data } = await client.get("/ocr/notifications");
  return data;
}

export async function clearNotification(notificationId: string): Promise<void> {
  await client.delete(`/ocr/notifications/${notificationId}`);
}

export default client;

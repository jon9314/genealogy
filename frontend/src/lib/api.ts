import axios from "axios";

import {
  Family,
  FamilyWithChildren,
  LineValidation,
  PageText,
  Person,
  ReparentRequest,
  Source,
  UpdatePersonPayload,
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

export async function runOCR(sourceId: number): Promise<{ pages: number; ocr_done: boolean }> {
  const { data } = await client.post(`/ocr/${sourceId}`);
  return data;
}

export async function getOCRStatus(sourceId: number): Promise<{ pages: number; ocr_done: boolean }> {
  const { data } = await client.get(`/ocr/${sourceId}`);
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

export async function parseSource(sourceId: number): Promise<{ people: number; families: number; flagged_lines: string[] }> {
  const { data } = await client.post(`/parse/${sourceId}`);
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

export default client;

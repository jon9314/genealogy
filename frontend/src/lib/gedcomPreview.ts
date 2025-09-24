import { exportGedcom } from "./api";

export async function getGedcomPreview(lines = 40): Promise<string[]> {
  const blob = await exportGedcom();
  const text = await blob.text();
  return text.trim().split(/\r?\n/).slice(0, lines);
}

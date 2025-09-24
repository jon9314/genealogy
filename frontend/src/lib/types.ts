export interface Source {
  id: number;
  name: string;
  path: string;
  pages: number;
  ocr_done: boolean;
}

export interface PageText {
  id: number;
  source_id: number;
  page_index: number;
  text: string;
}

export interface Person {
  id: number;
  chart_id: string | null;
  gen: number;
  name: string;
  given: string | null;
  surname: string | null;
  birth: string | null;
  death: string | null;
  sex: string | null;
  title: string | null;
  notes: string | null;
  source_id: number | null;
  page_index: number | null;
  line_index: number | null;
}

export interface UpdatePersonPayload {
  name?: string;
  given?: string | null;
  surname?: string | null;
  birth?: string | null;
  death?: string | null;
  sex?: string | null;
  title?: string | null;
  notes?: string | null;
  chart_id?: string | null;
}

export interface Family {
  id: number;
  husband_id: number | null;
  wife_id: number | null;
  notes: string | null;
}

export interface Child {
  id: number;
  family_id: number;
  person_id: number;
  order_index: number;
}

export interface FamilyWithChildren extends Family {
  children: Child[];
}

export interface ReparentRequest {
  person_id: number;
  new_family_id?: number | null;
  new_parent_person_id?: number | null;
}

export interface DuplicateCandidate {
  key: string;
  personIds: number[];
  summary: string;
}

export interface ApiError {
  message: string;
}

export interface ProjectDescriptor {
  filename: string;
}

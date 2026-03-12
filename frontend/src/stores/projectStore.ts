import { create } from "zustand";

export type PageStatus =
  | "pending" | "detecting" | "ocr" | "translating"
  | "inpainting" | "typesetting" | "review" | "done" | "error";

export interface PageRecord {
  id: string;
  index: number;
  filename: string;
  raw_path: string;
  clean_path: string | null;
  final_path: string | null;
  data_path: string | null;
  status: PageStatus;
  error_message: string | null;
}

export interface ProjectSettings {
  source_language: string;
  target_language: string;
  lmstudio_model: string | null;
  persona_prompt: string | null;
  max_concurrent_pages: number;
}

export interface Project {
  id: string;
  name: string;
  folder_path: string;
  created_at: string;
  updated_at: string;
  settings: ProjectSettings;
  pages: PageRecord[];
}

interface ProjectStore {
  project: Project | null;
  selectedPageIndex: number;
  isLoading: boolean;
  error: string | null;

  setProject: (project: Project) => void;
  setSelectedPage: (index: number) => void;
  clearProject: () => void;
  setError: (error: string | null) => void;
  setLoading: (loading: boolean) => void;
}

export const useProjectStore = create<ProjectStore>((set) => ({
  project: null,
  selectedPageIndex: 0,
  isLoading: false,
  error: null,

  setProject: (project) => set({ project, selectedPageIndex: 0, error: null }),
  setSelectedPage: (index) => set({ selectedPageIndex: index }),
  clearProject: () => set({ project: null, selectedPageIndex: 0 }),
  setError: (error) => set({ error }),
  setLoading: (isLoading) => set({ isLoading }),
}));
import { create } from "zustand";

type ThemeName = "light" | "dark" | "system";

type UiState = {
  sidebarOpen: boolean;
  theme: ThemeName;
  setSidebarOpen: (open: boolean) => void;
  setTheme: (theme: ThemeName) => void;
};

export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: false,
  theme: "system",
  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
  setTheme: (theme) => set({ theme }),
}));

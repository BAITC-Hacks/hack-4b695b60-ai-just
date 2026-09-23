import { createContext, useContext } from "react";
import type { Business, Meta, Team } from "@/api/types";
export interface Session {
  role: "business" | "team";
  businessId: number;
  teamId: number;
  meta: Meta;
  businesses: Business[];
  teams: Team[];
}
export const SessionContext = createContext<Session | null>(null);
export function useSession() {
  const value = useContext(SessionContext);
  if (!value) throw new Error("Сессия не загружена");
  return value;
}

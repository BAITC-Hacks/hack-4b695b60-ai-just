import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BrowserRouter,
  Link,
  NavLink,
  Navigate,
  Route,
  Routes,
  useNavigate,
} from "react-router";
import {
  BookOpen,
  BriefcaseBusiness,
  ChevronDown,
  CircleHelp,
  Compass,
  FlaskConical,
  LayoutGrid,
  ListChecks,
  Plus,
  RotateCcw,
  Sparkles,
  Trophy,
  Users,
  Zap,
} from "lucide-react";
import { Toaster, toast } from "sonner";
import { api, USE_MOCKS } from "./api/client";
import type { ProviderName } from "./api/types";
import { SessionContext } from "./lib/session";
import { Button } from "./components/ui/button";
import { Dialog } from "./components/ui/dialog";
import { ErrorState, Loading } from "./components/shared";
import { Builder } from "./features/Builder";
import { Catalog, PublicTask, Recommendations } from "./features/Catalog";
import { Leaderboard, MyTasks, Proposals } from "./features/Workspace";
function stored(key: string, fallback: string) {
  try {
    return localStorage.getItem(key) || fallback;
  } catch {
    return fallback;
  }
}
function save(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* Continue without persistent UI preferences. */
  }
}
function Shell() {
  const [role, setRole] = useState<"business" | "team">(() =>
    stored("sana-role", "business") === "team" ? "team" : "business",
  );
  const [businessId, setBusinessId] = useState(() =>
    Number(stored("sana-business", "1")),
  );
  const [teamId, setTeamId] = useState(() => Number(stored("sana-team", "1")));
  const [settings, setSettings] = useState(false);
  const [resetting, setResetting] = useState(false);
  const navigate = useNavigate();
  const cache = useQueryClient();
  const meta = useQuery({ queryKey: ["meta"], queryFn: api.meta });
  const businesses = useQuery({
    queryKey: ["businesses"],
    queryFn: api.businesses,
  });
  const teams = useQuery({ queryKey: ["teams"], queryFn: api.teams });
  const health = useQuery({ queryKey: ["health"], queryFn: api.health });
  const provider = useMutation({
    mutationFn: api.provider,
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["health"] });
      toast.success("Режим AI обновлён");
    },
    onError: (e) => toast.error(e.message),
  });
  const reset = useMutation({
    mutationFn: api.reset,
    onSuccess: async () => {
      cache.clear();
      setSettings(false);
      setResetting(false);
      navigate("/catalog");
      toast.success("Демо сброшено");
    },
    onError: (e) => toast.error(e.message),
  });
  const essential = [meta, businesses, teams];
  const error = essential.find((q) => q.isError);
  if (error)
    return (
      <div className="boot">
        <h1>AI Sana</h1>
        <ErrorState
          error={error.error}
          retry={() => essential.forEach((q) => void q.refetch())}
        />
      </div>
    );
  if (!meta.data || !businesses.data || !teams.data)
    return (
      <div className="boot">
        <Loading label="Открываем Challenge Hub…" />
      </div>
    );
  if (!businesses.data.length || !teams.data.length)
    return (
      <div className="boot">
        <ErrorState
          error={
            new Error(
              "Добавьте бизнесы и команды на сервере, затем повторите загрузку.",
            )
          }
          retry={() => essential.forEach((q) => void q.refetch())}
        />
      </div>
    );
  const activeBusiness = businesses.data.some((b) => b.id === businessId)
    ? businessId
    : businesses.data[0].id;
  const activeTeam = teams.data.some((t) => t.id === teamId)
    ? teamId
    : teams.data[0].id;
  const activeProvider = health.data?.ai.chain.find(
    (p) =>
      p.available &&
      (health.data.ai.mode === "auto" || p.name === health.data.ai.mode),
  );
  const providerLabels = {
    openai: "OpenAI",
    brev: "Brev",
    stub: "Офлайн",
  };
  const links =
    role === "business"
      ? [
          { to: "/builder", label: "Новая задача", icon: Plus },
          { to: "/my-tasks", label: "Мои задачи", icon: ListChecks },
          { to: "/catalog", label: "Каталог", icon: LayoutGrid },
          { to: "/leaderboard", label: "Лидерборд", icon: Trophy },
        ]
      : [
          { to: "/catalog", label: "Каталог", icon: LayoutGrid },
          { to: "/recommendations", label: "Рекомендации", icon: Sparkles },
          { to: "/proposals", label: "Мои отклики", icon: ListChecks },
          { to: "/leaderboard", label: "Лидерборд", icon: Trophy },
        ];
  return (
    <SessionContext.Provider
      value={{
        role,
        businessId: activeBusiness,
        teamId: activeTeam,
        meta: meta.data,
        businesses: businesses.data,
        teams: teams.data,
      }}
    >
      <div className="app-shell">
        <aside className="sidebar">
          <Link className="brand" to="/catalog">
            <div className="brand-mark">
              <Zap size={22} fill="currentColor" />
            </div>
            <div>
              AI Sana<span>CHALLENGE HUB</span>
            </div>
          </Link>
          <div className="workspace-label">РАБОЧЕЕ ПРОСТРАНСТВО</div>
          <nav>
            {links.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to}>
                <Icon size={19} />
                <span>{label}</span>
                {to === "/builder" && <span className="nav-dot" />}
              </NavLink>
            ))}
          </nav>
          <div className="sidebar-note">
            <div className="sidebar-note-icon">
              <Compass size={25} />
            </div>
            <h3>
              Идеи встречают
              <br />
              возможности
            </h3>
            <p>
              Бизнес-задачи.
              <br />
              Студенческие команды.
              <br />
              Реальные результаты.
            </p>
            <span>СОЗДАЁМ ВМЕСТЕ ↗</span>
          </div>
          <div className="sidebar-bottom">
            <span className="badge">AI SANA</span>
            <p>От знаний — к практике.</p>
          </div>
        </aside>
        <div className="main-shell">
          <header className="topbar">
            <span className="topbar-label">
              AI Sana Challenge Hub <span>/</span>{" "}
              {role === "business" ? "Для бизнеса" : "Для команд"}
            </span>
            <div className="topbar-controls">
              <div className="role-switch" aria-label="Роль">
                <button
                  className={role === "business" ? "active" : ""}
                  onClick={() => {
                    setRole("business");
                    save("sana-role", "business");
                    navigate("/my-tasks");
                  }}
                >
                  <BriefcaseBusiness size={15} />
                  Бизнес
                </button>
                <button
                  className={role === "team" ? "active" : ""}
                  onClick={() => {
                    setRole("team");
                    save("sana-role", "team");
                    navigate("/catalog");
                  }}
                >
                  <Users size={15} />
                  Команда
                </button>
              </div>
              <select
                aria-label={
                  role === "business" ? "Выбор бизнеса" : "Выбор команды"
                }
                className="identity-select"
                value={role === "business" ? activeBusiness : activeTeam}
                onChange={(e) => {
                  const value = Number(e.target.value);
                  if (role === "business") {
                    setBusinessId(value);
                    save("sana-business", String(value));
                    navigate("/my-tasks");
                  } else {
                    setTeamId(value);
                    save("sana-team", String(value));
                    navigate("/catalog");
                  }
                }}
              >
                {(role === "business" ? businesses.data : teams.data).map(
                  (p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ),
                )}
              </select>
              <button
                className="provider-button"
                onClick={() => setSettings(true)}
              >
                <span className={`dot ${health.isError ? "offline" : ""}`} />
                {health.isError
                  ? "Нет связи"
                  : activeProvider
                    ? providerLabels[activeProvider.name]
                    : "AI"}
                <ChevronDown size={12} />
              </button>
            </div>
          </header>
          {USE_MOCKS && (
            <div className="demo-notice">
              <FlaskConical size={14} />
              <span>
                Демонстрационный режим · данные хранятся только в этом браузере
              </span>
            </div>
          )}
          <main key={`${role}-${activeBusiness}-${activeTeam}`}>
            <Routes>
              <Route
                path="/"
                element={
                  <Navigate
                    to={role === "business" ? "/builder" : "/catalog"}
                    replace
                  />
                }
              />
              <Route path="/builder/:id?" element={<Builder />} />
              <Route path="/catalog" element={<Catalog />} />
              <Route path="/catalog/:id" element={<PublicTask />} />
              <Route
                path="/my-tasks"
                element={
                  role === "business" ? (
                    <MyTasks />
                  ) : (
                    <Navigate to="/catalog" replace />
                  )
                }
              />
              <Route
                path="/tasks/:id/proposals"
                element={
                  role === "business" ? (
                    <Proposals business />
                  ) : (
                    <Navigate to="/catalog" replace />
                  )
                }
              />
              <Route
                path="/recommendations"
                element={
                  role === "team" ? (
                    <Recommendations />
                  ) : (
                    <Navigate to="/catalog" replace />
                  )
                }
              />
              <Route
                path="/proposals"
                element={
                  role === "team" ? (
                    <Proposals />
                  ) : (
                    <Navigate to="/my-tasks" replace />
                  )
                }
              />
              <Route path="/leaderboard" element={<Leaderboard />} />
              <Route
                path="*"
                element={
                  <div className="empty">
                    <h1>Страница не найдена</h1>
                    <Link to="/catalog">В каталог →</Link>
                  </div>
                }
              />
            </Routes>
          </main>
          <footer>
            <span>AI Sana Challenge Hub</span>
            <span>Сильные идеи. Настоящие изменения.</span>
            <BookOpen size={15} />
          </footer>
        </div>
      </div>
      <Dialog
        open={settings}
        onOpenChange={setSettings}
        title="Настройки AI и демо"
        description="Переключение провайдера для новых запросов."
      >
        <label htmlFor="provider">AI-провайдер</label>
        <select
          id="provider"
          value={health.data?.ai.mode || "auto"}
          disabled={provider.isPending}
          onChange={(e) =>
            provider.mutate(e.target.value as "auto" | ProviderName)
          }
        >
          <option value="auto">Автоматически</option>
          {Object.entries(providerLabels).map(([key, label]) => (
            <option
              disabled={USE_MOCKS && key !== "stub"}
              key={key}
              value={key}
            >
              {label}
            </option>
          ))}
        </select>
        <p className="muted">
          {USE_MOCKS
            ? "В демонстрационном режиме AI не вызывается. Доступна локальная имитация ответов."
            : activeProvider?.name === "stub"
              ? "AI работает локально: внешние сервисы недоступны"
              : "Недоступные провайдеры заменяются следующими из цепочки."}
        </p>
        {health.isError && (
          <ErrorState
            error={health.error}
            retry={() => void health.refetch()}
          />
        )}
        <hr />
        {resetting ? (
          <div className="warning">
            <p>
              Удалить изменения задач, отклики и этапы и восстановить исходные
              демоданные?
            </p>
            <div className="row">
              <Button
                variant="destructive"
                disabled={reset.isPending}
                onClick={() => reset.mutate()}
              >
                Да, сбросить демо
              </Button>
              <Button variant="secondary" onClick={() => setResetting(false)}>
                Отмена
              </Button>
            </div>
          </div>
        ) : (
          <Button variant="secondary" onClick={() => setResetting(true)}>
            <RotateCcw size={16} />
            Сбросить демо
          </Button>
        )}
        {reset.isError && <p className="error-text">{reset.error.message}</p>}
        <p className="small muted">
          <CircleHelp size={13} /> Ручное переключение не меняет ранее
          подтверждённые поля.
        </p>
      </Dialog>
    </SessionContext.Provider>
  );
}
export default function App() {
  return (
    <BrowserRouter>
      <Shell />
      <Toaster richColors position="bottom-right" closeButton />
    </BrowserRouter>
  );
}

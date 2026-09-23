import { useState, type KeyboardEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Dialog } from "@/components/ui/dialog";
import { Empty, ErrorState, Loading } from "@/components/shared";
type InspectorTab = "traces" | "prompts";
const inspectorTabs: InspectorTab[] = ["traces", "prompts"];
export function Inspector({
  taskId,
  open,
  onOpenChange,
}: {
  taskId: number;
  open: boolean;
  onOpenChange: (value: boolean) => void;
}) {
  const [tab, setTab] = useState<InspectorTab>("traces");
  const tabId = (value: InspectorTab) => `inspector-tab-${taskId}-${value}`;
  const panelId = (value: InspectorTab) => `inspector-panel-${taskId}-${value}`;
  const selectTab = (value: InspectorTab) => {
    setTab(value);
    document.getElementById(tabId(value))?.focus();
  };
  const handleTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const currentIndex = inspectorTabs.indexOf(tab);
    let nextIndex: number | undefined;
    if (event.key === "ArrowRight") {
      nextIndex = (currentIndex + 1) % inspectorTabs.length;
    } else if (event.key === "ArrowLeft") {
      nextIndex =
        (currentIndex - 1 + inspectorTabs.length) % inspectorTabs.length;
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = inspectorTabs.length - 1;
    }
    if (nextIndex === undefined) return;
    event.preventDefault();
    selectTab(inspectorTabs[nextIndex]);
  };
  const traces = useQuery({
    queryKey: ["traces", taskId],
    queryFn: () => api.traces(taskId),
    enabled: open,
  });
  const prompts = useQuery({
    queryKey: ["prompts"],
    queryFn: api.prompts,
    enabled: open && tab === "prompts",
  });
  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="AI Inspector"
      description="Прозрачность каждого предложения: источник, промпт и проверка фактов."
      sheet
    >
      <div className="tabs" role="tablist" aria-label="Разделы AI Inspector">
        <button
          type="button"
          role="tab"
          id={tabId("traces")}
          aria-controls={panelId("traces")}
          aria-selected={tab === "traces"}
          aria-label="Вызовы AI"
          tabIndex={tab === "traces" ? 0 : -1}
          className={tab === "traces" ? "active" : ""}
          onClick={() => setTab("traces")}
          onKeyDown={handleTabKeyDown}
        >
          Вызовы AI
        </button>
        <button
          type="button"
          role="tab"
          id={tabId("prompts")}
          aria-controls={panelId("prompts")}
          aria-selected={tab === "prompts"}
          aria-label="Промпты и схемы"
          tabIndex={tab === "prompts" ? 0 : -1}
          className={tab === "prompts" ? "active" : ""}
          onClick={() => setTab("prompts")}
          onKeyDown={handleTabKeyDown}
        >
          Промпты и схемы
        </button>
      </div>
      <div
        role="tabpanel"
        id={panelId("traces")}
        aria-labelledby={tabId("traces")}
        hidden={tab !== "traces"}
        tabIndex={0}
      >
        {traces.isPending ? (
          <Loading />
        ) : traces.isError ? (
          <ErrorState
            error={traces.error}
            retry={() => void traces.refetch()}
          />
        ) : traces.data.length ? (
          traces.data.map((t) => (
            <details className="trace" key={t.id}>
              <summary>
                <strong>{t.operation}</strong>
                <span className={`badge trace-${t.status}`}>{t.status}</span>
                <p>
                  {t.provider} · {t.model} · {t.latency_ms} мс
                </p>
              </summary>
              <p>Версия промпта: {t.prompt_version || "—"}</p>
              <h4>Вход с маскированием данных</h4>
              <pre>{t.input_redacted}</pre>
              <h4>Сырой ответ</h4>
              <pre>{t.raw_output}</pre>
              <h4>Распарсенный JSON</h4>
              <pre>{JSON.stringify(t.parsed, null, 2)}</pre>
              {t.errors.map((e, i) => (
                <p className="warning" key={i}>
                  {e}
                </p>
              ))}
              {t.grounding_rejected.map((r, i) => (
                <div className="error-box" key={i}>
                  {r.field}: отклонено — {r.reason}
                  <br />
                  {r.value}
                </div>
              ))}
            </details>
          ))
        ) : (
          <Empty title="Вызовов пока нет">
            Создайте задачу или задайте дополнительные вопросы.
          </Empty>
        )}
      </div>
      <div
        role="tabpanel"
        id={panelId("prompts")}
        aria-labelledby={tabId("prompts")}
        hidden={tab !== "prompts"}
        tabIndex={0}
      >
        {tab === "prompts" &&
          (prompts.isPending ? (
            <Loading />
          ) : prompts.isError ? (
            <ErrorState
              error={prompts.error}
              retry={() => void prompts.refetch()}
            />
          ) : (
            prompts.data.map((p) => (
              <details className="trace" key={`${p.name}-${p.version}`}>
                <summary>
                  {p.name} · {p.version}
                </summary>
                <h4>Системный промпт</h4>
                <pre>{p.system}</pre>
                <h4>Шаблон</h4>
                <pre>{p.user_template}</pre>
                <h4>Схема</h4>
                <pre>{JSON.stringify(p.output_schema, null, 2)}</pre>
              </details>
            ))
          ))}
      </div>
    </Dialog>
  );
}

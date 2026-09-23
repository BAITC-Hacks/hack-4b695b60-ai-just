import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Dialog } from "@/components/ui/dialog";
import { Empty, ErrorState, Loading } from "@/components/shared";
export function Inspector({
  taskId,
  open,
  onOpenChange,
}: {
  taskId: number;
  open: boolean;
  onOpenChange: (value: boolean) => void;
}) {
  const [tab, setTab] = useState("traces");
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
      <div className="tabs">
        <button
          className={tab === "traces" ? "active" : ""}
          onClick={() => setTab("traces")}
        >
          Вызовы AI
        </button>
        <button
          className={tab === "prompts" ? "active" : ""}
          onClick={() => setTab("prompts")}
        >
          Промпты и схемы
        </button>
      </div>
      {tab === "traces" ? (
        traces.isPending ? (
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
        )
      ) : prompts.isPending ? (
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
      )}
    </Dialog>
  );
}

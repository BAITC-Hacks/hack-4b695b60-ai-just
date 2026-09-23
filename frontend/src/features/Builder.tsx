import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCheck,
  ChevronDown,
  CircleHelp,
  FileText,
  Send,
  Sparkles,
  WandSparkles,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { api, USE_MOCKS } from "@/api/client";
import type { CardField, FieldKey, TaskDetail } from "@/api/types";
import { useSession } from "@/lib/session";
import { pluralize } from "@/lib/text";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Select } from "@/components/ui/select";
import {
  ErrorState,
  LevelBadge,
  Loading,
  PageHeading,
} from "@/components/shared";
import { RatingPanel } from "@/components/RatingPanel";
import { Inspector } from "./Inspector";
const example =
  "Хотим чат-бота для клиентов, чтобы меньше звонили в колл-центр.";
type FieldFeedback = "success" | "rejected";
export function Builder() {
  const { id } = useParams();
  const { role, businessId } = useSession();
  const query = useQuery({
    queryKey: ["task", Number(id)],
    queryFn: () => api.task(Number(id)),
    enabled: !!id,
  });
  if (role !== "business")
    return (
      <div className="panel">
        <h2>Конструктор доступен бизнесу</h2>
        <p>Переключите роль в шапке, чтобы создать задачу.</p>
        <Link to="/catalog">Перейти в каталог</Link>
      </div>
    );
  if (!id) return <Draft key={businessId} />;
  if (query.isPending) return <Loading />;
  if (query.isError)
    return (
      <ErrorState error={query.error} retry={() => void query.refetch()} />
    );
  if (query.data.business.id !== businessId)
    return (
      <div className="panel">
        <h2>Задача другого бизнеса</h2>
        <p>Выберите «{query.data.business.name}» в шапке для редактирования.</p>
      </div>
    );
  return <Editor key={id} task={query.data} />;
}
function Steps({ step }: { step: number }) {
  const steps = [
    ["Черновик", "Опишите идею"],
    ["Уточнение", "Ответьте AI"],
    ["Карточка", "Проверьте факты"],
    ["Публикация", "Откройте командам"],
  ];
  return (
    <ol className="steps" aria-label="Этапы создания задачи">
      {steps.map(([label, hint], i) => (
        <li
          className={i === step ? "current" : i < step ? "complete" : ""}
          key={label}
          aria-current={i === step ? "step" : undefined}
        >
          <span>{i < step ? <Check size={15} /> : `0${i + 1}`}</span>
          <div>
            <b>{label}</b>
            <small>{hint}</small>
          </div>
        </li>
      ))}
    </ol>
  );
}
function AnalyzeProgress() {
  const stages = ["Читаем черновик", "Ищем пробелы", "Готовим вопросы"];
  const [stage, setStage] = useState(0);
  useEffect(() => {
    const timers = [
      window.setTimeout(() => setStage(1), 3000),
      window.setTimeout(() => setStage(2), 6000),
    ];
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, []);
  return (
    <div
      className="loading ai-analysis-progress"
      role="status"
      aria-live="polite"
      aria-atomic="true"
      data-stage={stage + 1}
    >
      <Sparkles className="spin" size={23} aria-hidden="true" />
      <p>
        <strong>{stages[stage]}</strong>
      </p>
      <div className="row ai-analysis-steps" aria-label="Этапы анализа">
        {stages.map((label, index) => (
          <span
            className={`badge ai-analysis-step ${index < stage ? "complete" : index === stage ? "current" : "pending"}`}
            key={label}
          >
            {index < stage ? <Check size={12} aria-hidden="true" /> : index + 1}
            {label}
          </span>
        ))}
      </div>
      <progress
        max={stages.length}
        value={stage + 1}
        aria-label={`Анализ черновика: шаг ${stage + 1} из ${stages.length}`}
      />
    </div>
  );
}
function Draft() {
  const { businessId, meta } = useSession();
  const navigate = useNavigate();
  const createLock = useRef(false);
  const [draft, setDraft] = useState("");
  const [topic, setTopic] = useState("");
  const create = useMutation({
    mutationFn: () => api.create(businessId, draft.trim(), topic),
    onSuccess: (t) => navigate(`/builder/${t.id}`),
  });
  return (
    <>
      <PageHeading
        eyebrow="ОТ ИДЕИ К РЕШЕНИЮ"
        title="Дайте вашей задаче начало"
      >
        Расскажите о проблеме. AI поможет превратить её в понятный вызов для
        команды.
      </PageHeading>
      <Steps step={0} />
      <div className="builder-layout">
        <div>
          <form
            className="panel draft-panel"
            onSubmit={(e) => {
              e.preventDefault();
              if (createLock.current || create.isPending) return;
              createLock.current = true;
              create.mutate(undefined, {
                onSettled: () => {
                  createLock.current = false;
                },
              });
            }}
          >
            <div className="draft-heading">
              <div className="section-icon">
                <FileText size={23} />
              </div>
              <div>
                <h2>Что вы хотите решить?</h2>
                <p className="muted">
                  Начните с пары предложений. Необязательно знать все ответы
                  сразу.
                </p>
              </div>
            </div>
            <label htmlFor="draft">Описание задачи</label>
            <textarea
              id="draft"
              className="draft-input"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={example}
              minLength={10}
              maxLength={4000}
              required
              disabled={create.isPending}
            />
            <div className="row between">
              <button
                type="button"
                className="text-link"
                onClick={() => setDraft(example)}
                disabled={create.isPending}
              >
                <Sparkles size={14} />
                Попробовать пример
              </button>
              <small className="field-counter">{draft.length} / 4000</small>
            </div>
            <label htmlFor="topic">Тема задачи</label>
            <Select
              id="topic"
              label="Тема задачи"
              value={topic}
              onValueChange={setTopic}
              disabled={create.isPending}
              options={[
                { value: "", label: "Выберите тему · необязательно" },
                ...meta.topics.map((t) => ({ value: t.key, label: t.label })),
              ]}
            />
            <div className="draft-footer">
              <span className="muted">
                <CircleHelp size={15} /> Обычно занимает пару минут
              </span>
              <Button
                type="submit"
                disabled={create.isPending || draft.trim().length < 10}
              >
                <WandSparkles size={17} />
                {create.isPending ? "Анализируем…" : "Проанализировать"}
                <ArrowRight size={16} />
              </Button>
            </div>
            {create.isPending && <AnalyzeProgress />}
            {create.isError && <ErrorState error={create.error} />}
          </form>
          <div className="trust-note">
            <CheckCheck size={17} />
            <span>
              Вы управляете результатом. AI предлагает — вы проверяете и
              подтверждаете.
            </span>
          </div>
        </div>
        <aside className="intro-panel">
          <span className="eyebrow">КАК ЭТО РАБОТАЕТ</span>
          <h2>
            Одна идея.
            <br />
            Больше возможностей.
          </h2>
          <div className="intro-orbit">
            <div className="orbit-ring" />
            <div className="orbit-center">
              <Sparkles size={34} />
            </div>
            <span className="orbit-tag tag-one">Понятная задача</span>
            <span className="orbit-tag tag-two">Сильная команда</span>
            <span className="orbit-dot" />
          </div>
          {[
            [
              "01",
              "Опишите проблему",
              "Свободным текстом, как рассказали бы коллеге.",
            ],
            ["02", "Уточните с AI", "Ответьте на вопросы и подтвердите факты."],
            [
              "03",
              "Найдите команду",
              "Опубликуйте задачу и выбирайте из откликов.",
            ],
          ].map(([n, h, p]) => (
            <div className="intro-step" key={n}>
              <span>{n}</span>
              <div>
                <b>{h}</b>
                <p>{p}</p>
              </div>
            </div>
          ))}
          <div className="intro-bottom">
            Хорошие решения начинаются
            <br />с хороших вопросов.
          </div>
        </aside>
      </div>
    </>
  );
}
function FieldEditor({
  fieldKey,
  field,
  label,
  placeholder,
  busy,
  patch,
  feedback,
}: {
  fieldKey: FieldKey;
  field: CardField;
  label: string;
  placeholder: string;
  busy: boolean;
  patch: (
    key: FieldKey,
    change: { value?: string; confirm?: boolean; reject?: boolean },
    feedback: FieldFeedback,
  ) => Promise<unknown>;
  feedback?: FieldFeedback;
}) {
  const [value, setValue] = useState(field.value || "");
  const [expanded, setExpanded] = useState(field.status !== "confirmed");
  const dirty = value !== (field.value || "");
  return (
    <section
      id={`field-section-${fieldKey}`}
      className={`field-card field-${field.status} ${expanded ? "expanded" : "collapsed"} ${feedback ? `field-action-${feedback}` : ""}`}
      data-feedback={feedback}
    >
      <div className="row between">
        <button
          type="button"
          className="field-heading"
          aria-expanded={expanded}
          aria-controls={`field-content-${fieldKey}`}
          aria-disabled={dirty}
          title={dirty ? "Сначала сохраните или отмените изменения" : undefined}
          onClick={() => {
            if (!dirty) setExpanded((current) => !current);
          }}
        >
          <ChevronDown size={16} />
          <span>{label}</span>
        </button>
        <span className={`badge status-${field.status}`}>
          {field.status === "confirmed"
            ? "Подтверждено"
            : field.status === "suggested"
              ? "Предложено AI"
              : "Пусто"}
        </span>
      </div>
      {!expanded && (
        <button
          type="button"
          className="field-preview"
          onClick={() => setExpanded(true)}
        >
          {field.value || placeholder}
        </button>
      )}
      <div
        id={`field-content-${fieldKey}`}
        className="field-content"
        hidden={!expanded}
      >
        <label className="sr-only" htmlFor={`field-${fieldKey}`}>
          {label}
        </label>
        <textarea
          id={`field-${fieldKey}`}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder}
          maxLength={2000}
          rows={fieldKey === "title" ? 2 : 3}
          disabled={busy}
        />
        {field.status === "suggested" && (
          <details className="evidence">
            <summary>
              На основании вашего текста · {field.evidence.length} цитат
            </summary>
            {field.evidence.map((e, i) => (
              <blockquote key={i}>
                «{e.quote}»<cite>Источник: {e.source}</cite>
              </blockquote>
            ))}
          </details>
        )}
        <div className="row field-actions">
          {dirty && (
            <>
              <Button
                className="field-action-save"
                size="sm"
                disabled={busy}
                onClick={() =>
                  void patch(fieldKey, { value }, "success").catch(
                    () => undefined,
                  )
                }
              >
                Сохранить
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={busy}
                onClick={() => setValue(field.value || "")}
              >
                Отменить
              </Button>
            </>
          )}
          {field.status === "suggested" && !dirty && (
            <>
              <Button
                className="field-action-confirm"
                size="sm"
                variant="secondary"
                disabled={busy}
                onClick={() =>
                  void patch(fieldKey, { confirm: true }, "success").catch(
                    () => undefined,
                  )
                }
              >
                <Check size={14} />
                Подтвердить
              </Button>
              <Button
                className="field-action-reject"
                size="sm"
                variant="ghost"
                disabled={busy}
                onClick={() =>
                  void patch(fieldKey, { reject: true }, "rejected").catch(
                    () => undefined,
                  )
                }
              >
                <X size={14} />
                Отклонить
              </Button>
            </>
          )}
        </div>
      </div>
      {feedback && (
        <span className="sr-only" role="status">
          {feedback === "rejected"
            ? `${label}: предложение отклонено`
            : `${label}: изменение сохранено`}
        </span>
      )}
    </section>
  );
}
function Editor({ task }: { task: TaskDetail }) {
  const { meta } = useSession();
  const cache = useQueryClient();
  const [view, setView] = useState<"questions" | "card">(
    task.status === "clarifying" ? "questions" : "card",
  );
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [publishing, setPublishing] = useState(false);
  const [checked, setChecked] = useState(false);
  const [success, setSuccess] = useState(false);
  const [inspector, setInspector] = useState(false);
  const [fieldFeedback, setFieldFeedback] = useState<{
    field: FieldKey;
    state: FieldFeedback;
  } | null>(null);
  const actionLock = useRef(false);
  const feedbackTimer = useRef<number | undefined>(undefined);
  useEffect(
    () => () => {
      if (feedbackTimer.current !== undefined)
        window.clearTimeout(feedbackTimer.current);
    },
    [],
  );
  const mutation = useMutation({
    mutationFn: (action: () => Promise<TaskDetail>) => action(),
    onSuccess: (t) => {
      cache.setQueryData(["task", t.id], t);
      void cache.invalidateQueries({
        predicate: (q) => q.queryKey[0] !== "task",
      });
    },
    onError: (e) => toast.error(e.message),
  });
  const act = async (action: () => Promise<TaskDetail>) => {
    if (actionLock.current) throw new Error("Действие уже выполняется");
    actionLock.current = true;
    try {
      return await mutation.mutateAsync(action);
    } finally {
      actionLock.current = false;
    }
  };
  const showFieldFeedback = (field: FieldKey, state: FieldFeedback) => {
    setFieldFeedback({ field, state });
    if (feedbackTimer.current !== undefined)
      window.clearTimeout(feedbackTimer.current);
    feedbackTimer.current = window.setTimeout(() => {
      setFieldFeedback((current) =>
        current?.field === field && current.state === state ? null : current,
      );
      feedbackTimer.current = undefined;
    }, 900);
  };
  const patch = async (
    field: FieldKey,
    change: { value?: string; confirm?: boolean; reject?: boolean },
    feedback: FieldFeedback,
  ) => {
    setFieldFeedback((current) => (current?.field === field ? null : current));
    const result = await act(() => api.patch(task.id, { [field]: change }));
    showFieldFeedback(field, feedback);
    return result;
  };
  const confirm = () => {
    void act(() => api.confirm(task.id)).catch(() => undefined);
  };
  const round = Math.max(1, ...task.questions.map((q) => q.round));
  const questions = task.questions.filter((q) => q.round === round);
  const confirmedCount = Object.values(task.card).filter(
    (field) => field.status === "confirmed",
  ).length;
  const unconfirmedCount = meta.fields.length - confirmedCount;
  const focus = (field: FieldKey) => {
    setView("card");
    window.setTimeout(() => {
      const section = document.getElementById(`field-section-${field}`);
      const el = document.getElementById(`field-${field}`);
      const content = document.getElementById(`field-content-${field}`);
      section?.scrollIntoView({
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "auto"
          : "smooth",
        block: "center",
      });
      if (el && !content?.hidden) {
        el.focus();
        return;
      }
      const toggle =
        section?.querySelector<HTMLButtonElement>(".field-heading");
      toggle?.click();
      window.setTimeout(() => {
        document.getElementById(`field-${field}`)?.focus();
      }, 0);
    }, 80);
  };
  return (
    <>
      <PageHeading
        eyebrow={`ЗАДАЧА #${task.id} · ${task.business.name}`}
        title={
          success
            ? "Задача опубликована!"
            : view === "questions"
              ? "Уточним самое важное"
              : "Сделаем задачу понятной"
        }
        action={
          <Button variant="secondary" onClick={() => setInspector(true)}>
            <CircleHelp size={16} />
            Как это работает
          </Button>
        }
      >
        {success
          ? `Место в каталоге — №${task.catalog_position}. Команды уже могут откликаться.`
          : "Каждый подтверждённый факт делает задачу ближе к решению."}
      </PageHeading>
      <Steps
        step={
          success || task.status === "published"
            ? 3
            : view === "questions"
              ? 1
              : 2
        }
      />
      <div className={`mobile-rating-summary score-${task.rating.level.key}`}>
        <div className="mobile-rating-topline">
          <span>Готовность задачи</span>
          <LevelBadge level={task.rating.level} />
        </div>
        <div className="mobile-rating-score">
          <strong>{task.rating.score}</strong>
          <span>/100</span>
          {task.rating.delta > 0 && <b>+{task.rating.delta}</b>}
        </div>
        <progress
          max="100"
          value={task.rating.score}
          aria-label={`Готовность задачи: ${task.rating.score} из 100`}
        />
        <div className="mobile-rating-bottomline">
          <span>
            {task.rating.next_level
              ? `До «${task.rating.next_level.label}» — ${task.rating.next_level.points_needed}`
              : "Максимальный уровень достигнут"}
          </span>
          {task.rating.potential_score > task.rating.score && (
            <button
              type="button"
              onClick={confirm}
              disabled={mutation.isPending}
            >
              Подтвердить +{task.rating.potential_score - task.rating.score}
            </button>
          )}
        </div>
      </div>
      {success && (
        <div className="success-banner">
          <CheckCheck size={23} />
          <span>
            Готово! {task.rating.level.label} · {task.rating.score} баллов
          </span>
          <Button asChild>
            <Link to={`/catalog/${task.id}`}>
              Открыть в каталоге
              <ArrowRight size={16} />
            </Link>
          </Button>
        </div>
      )}
      <div className="builder-layout">
        <div>
          {view === "questions" ? (
            <>
              <form
                className="panel"
                onSubmit={(e) => {
                  e.preventDefault();
                  void act(() =>
                    api.answers(
                      task.id,
                      questions.map((q) => ({
                        question_id: q.id,
                        text: (answers[q.id] ?? q.answer ?? "").trim(),
                      })),
                    ),
                  )
                    .then(() => setView("card"))
                    .catch(() => undefined);
                }}
              >
                <div className="row between">
                  <h2>Несколько вопросов от AI</h2>
                  <span className="badge purple">Раунд {round}</span>
                </div>
                <p className="muted">
                  Можно пропустить вопрос и вернуться к нему позже.
                </p>
                {questions.map((q, i) => (
                  <div className="question" key={q.id}>
                    <div className="row between">
                      <span className="topic">
                        {meta.fields.find((f) => f.key === q.field)?.label}
                      </span>
                      <span className="gain">+{q.points_gain} баллов</span>
                    </div>
                    <label htmlFor={q.id}>
                      {i + 1}. {q.question}
                    </label>
                    <p className="muted">{q.why}</p>
                    <textarea
                      id={q.id}
                      value={answers[q.id] ?? q.answer ?? ""}
                      onChange={(e) =>
                        setAnswers({ ...answers, [q.id]: e.target.value })
                      }
                      maxLength={2000}
                      placeholder="Ваш ответ…"
                      rows={3}
                      disabled={mutation.isPending}
                    />
                  </div>
                ))}
                <div className="row between">
                  <Button
                    variant="ghost"
                    type="button"
                    onClick={() => setView("card")}
                  >
                    Перейти к полям
                  </Button>
                  <Button disabled={mutation.isPending} type="submit">
                    {mutation.isPending ? "Собираем…" : "Собрать карточку"}
                    <ArrowRight size={16} />
                  </Button>
                </div>
              </form>
              <div className="panel discovered">
                <h3>
                  <Sparkles size={18} />
                  AI нашёл в тексте
                </h3>
                {meta.fields
                  .filter((f) => task.card[f.key].status === "suggested")
                  .map((f) => (
                    <FieldEditor
                      key={`${f.key}-${task.card[f.key].value}-${task.card[f.key].status}`}
                      fieldKey={f.key}
                      field={task.card[f.key]}
                      label={f.label}
                      placeholder={f.placeholder}
                      busy={mutation.isPending}
                      patch={patch}
                      feedback={
                        fieldFeedback?.field === f.key
                          ? fieldFeedback.state
                          : undefined
                      }
                    />
                  ))}
              </div>
            </>
          ) : (
            <>
              <div className="editor-toolbar">
                <div className="editor-progress-copy">
                  <span>Заполнение карточки</span>
                  <b>
                    {confirmedCount} из {meta.fields.length}
                  </b>
                </div>
                <progress
                  max={meta.fields.length}
                  value={confirmedCount}
                  aria-label={`${confirmedCount} из ${meta.fields.length} полей подтверждено`}
                />
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={mutation.isPending}
                  onClick={() =>
                    void act(() => api.clarify(task.id))
                      .then(() => setView("questions"))
                      .catch(() => undefined)
                  }
                >
                  <Sparkles size={15} />
                  Задать ещё вопросы
                </Button>
              </div>
              {meta.fields.map((f) => (
                <FieldEditor
                  key={`${f.key}-${task.card[f.key].value}-${task.card[f.key].status}`}
                  fieldKey={f.key}
                  field={task.card[f.key]}
                  label={f.label}
                  placeholder={f.placeholder}
                  busy={mutation.isPending}
                  patch={patch}
                  feedback={
                    fieldFeedback?.field === f.key
                      ? fieldFeedback.state
                      : undefined
                  }
                />
              ))}
              <div className="publish-bar">
                <Button variant="ghost" onClick={() => setView("questions")}>
                  <ArrowLeft size={16} />К вопросам
                </Button>
                {task.status === "published" ? (
                  <Button asChild>
                    <Link to={`/catalog/${task.id}`}>Открыть публикацию</Link>
                  </Button>
                ) : (
                  <Button
                    disabled={mutation.isPending}
                    onClick={() => {
                      setChecked(false);
                      setPublishing(true);
                    }}
                  >
                    <Send size={16} />
                    Опубликовать задачу
                  </Button>
                )}
              </div>
            </>
          )}
          {mutation.isError && <ErrorState error={mutation.error} />}
        </div>
        <RatingPanel
          rating={task.rating}
          taskId={task.id}
          position={task.catalog_position ?? task.catalog_position_preview}
          onConfirm={confirm}
          onFocus={focus}
          busy={mutation.isPending}
        />
      </div>
      <Dialog
        open={publishing}
        onOpenChange={setPublishing}
        title="Готовы показать задачу командам?"
        description="В публичной карточке будут только подтверждённые вами факты."
      >
        <p className="warning">
          {unconfirmedCount === 0
            ? "Все поля подтверждены и попадут в публичную карточку."
            : `${unconfirmedCount} ${pluralize(unconfirmedCount, "поле", "поля", "полей")} не ${unconfirmedCount === 1 ? "подтверждено" : "подтверждены"} и не ${unconfirmedCount === 1 ? "попадёт" : "попадут"} в карточку.`}
        </p>
        {task.card.title.status !== "confirmed" && (
          <p className="error-text">Сначала подтвердите название задачи.</p>
        )}
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => setChecked(e.target.checked)}
          />
          Я проверил карточку
        </label>
        <Button
          disabled={
            !checked ||
            mutation.isPending ||
            task.card.title.status !== "confirmed"
          }
          onClick={() =>
            void act(() => api.publish(task.id))
              .then(() => {
                setPublishing(false);
                setSuccess(true);
                toast.success("Задача опубликована");
              })
              .catch(() => undefined)
          }
        >
          Опубликовать
        </Button>
        {mutation.isError && (
          <p className="error-text">{mutation.error.message}</p>
        )}
        {USE_MOCKS && (
          <p className="muted small">
            Публикация в демонстрационном каталоге этого браузера.
          </p>
        )}
      </Dialog>
      <Inspector
        taskId={task.id}
        open={inspector}
        onOpenChange={setInspector}
      />
    </>
  );
}

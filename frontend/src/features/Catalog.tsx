import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import {
  ArrowLeft,
  ArrowRight,
  CircleHelp,
  Search,
  Send,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "@/api/client";
import { useSession } from "@/lib/session";
import { Button } from "@/components/ui/button";
import {
  Empty,
  ErrorState,
  Loading,
  PageHeading,
  TaskTile,
} from "@/components/shared";
import { RatingPanel } from "@/components/RatingPanel";
import { Inspector } from "./Inspector";
export function Catalog() {
  const { meta, role } = useSession();
  const [search, setSearch] = useState("");
  const [topic, setTopic] = useState("");
  const [levels, setLevels] = useState<string[]>([]);
  const [sort, setSort] = useState("rating");
  const [page, setPage] = useState(0);
  const params = new URLSearchParams({
    sort,
    limit: "12",
    offset: String(page * 12),
  });
  if (search) params.set("q", search);
  if (topic) params.set("topic", topic);
  levels.forEach((l) => params.append("level", l));
  const query = useQuery({
    queryKey: ["catalog", params.toString()],
    queryFn: () => api.catalog(params),
  });
  return (
    <>
      <PageHeading
        eyebrow="ИДЕИ СТАНОВЯТСЯ РЕШЕНИЯМИ"
        title="Задачи с реальным смыслом"
        action={
          role === "business" && (
            <Button asChild>
              <Link to="/builder">
                Создать задачу
                <ArrowRight size={16} />
              </Link>
            </Button>
          )
        }
      >
        Находите вызовы, применяйте знания и создавайте то, что нужно бизнесу.
      </PageHeading>
      <div className="catalog-hero">
        <div>
          <span className="eyebrow">ОТКРЫТЫЙ КАТАЛОГ</span>
          <h2>
            Ваш следующий проект
            <br />
            начинается здесь.
          </h2>
          <p>
            Любая команда может откликнуться на любую задачу.
            <br />
            Рейтинг показывает готовность, а не ограничивает выбор.
          </p>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="hero-card c1">
            <span>ГОТОВНОСТЬ</span>
            <strong>
              96<small>/100</small>
            </strong>
            <div className="mini-track" />
            <b>✦ Приоритетная</b>
          </div>
          <div className="hero-star">✳</div>
        </div>
      </div>
      <div className="filters">
        <div className="search-box">
          <Search size={18} />
          <input
            aria-label="Поиск задач"
            placeholder="Найти задачу по названию или описанию"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(0);
            }}
          />
        </div>
        <select
          aria-label="Тема"
          value={topic}
          onChange={(e) => {
            setTopic(e.target.value);
            setPage(0);
          }}
        >
          <option value="">Все темы</option>
          {meta.topics.map((t) => (
            <option key={t.key} value={t.key}>
              {t.label}
            </option>
          ))}
        </select>
        <select
          aria-label="Сортировка"
          value={sort}
          onChange={(e) => {
            setSort(e.target.value);
            setPage(0);
          }}
        >
          <option value="rating">По рейтингу</option>
          <option value="newest">Сначала новые</option>
        </select>
      </div>
      <div className="level-filters">
        <button
          className={!levels.length ? "active" : ""}
          onClick={() => {
            setLevels([]);
            setPage(0);
          }}
        >
          Все уровни
        </button>
        {meta.levels.map((l) => (
          <button
            aria-pressed={levels.includes(l.key)}
            className={levels.includes(l.key) ? "active" : ""}
            key={l.key}
            onClick={() => {
              setLevels(
                levels.includes(l.key)
                  ? levels.filter((k) => k !== l.key)
                  : [...levels, l.key],
              );
              setPage(0);
            }}
          >
            {l.label}
          </button>
        ))}
        <span>{query.data ? `${query.data.total} задач` : ""}</span>
      </div>
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <ErrorState error={query.error} retry={() => void query.refetch()} />
      ) : query.data.items.length ? (
        <>
          <div className="task-grid">
            {query.data.items.map((t) => (
              <TaskTile key={t.id} task={t} />
            ))}
          </div>
          {query.data.total > 12 && (
            <div className="pagination">
              <Button
                variant="secondary"
                disabled={!page}
                onClick={() => setPage(page - 1)}
              >
                Назад
              </Button>
              <span>Страница {page + 1}</span>
              <Button
                variant="secondary"
                disabled={(page + 1) * 12 >= query.data.total}
                onClick={() => setPage(page + 1)}
              >
                Далее
              </Button>
            </div>
          )}
        </>
      ) : (
        <Empty title="Задачи не найдены">
          <p>Попробуйте другой запрос или сбросьте фильтры.</p>
          <Button
            variant="secondary"
            onClick={() => {
              setSearch("");
              setTopic("");
              setLevels([]);
              setPage(0);
            }}
          >
            Сбросить фильтры
          </Button>
        </Empty>
      )}
    </>
  );
}
export function Recommendations() {
  const { teamId, teams } = useSession();
  const query = useQuery({
    queryKey: ["recommendations", teamId],
    queryFn: () => api.recommendations(teamId),
  });
  return (
    <>
      <PageHeading
        eyebrow="ПОДОБРАНО ПО НАВЫКАМ"
        title={`Для команды ${teams.find((t) => t.id === teamId)?.name || ""}`}
      >
        Ваши интересы и технологии помогут найти точку приложения сил.
      </PageHeading>
      <div className="info-banner">
        <Sparkles size={20} />
        <span>
          Рекомендации не ограничивают каталог.{" "}
          <Link to="/catalog">Смотреть все задачи →</Link>
        </span>
      </div>
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <ErrorState error={query.error} retry={() => void query.refetch()} />
      ) : (
        <>
          <p className="muted">Метод: {query.data.method}</p>
          {query.data.items.length ? (
            <div className="task-grid">
              {query.data.items.map((r) => (
                <div className="recommendation" key={r.task.id}>
                  <div className="match">
                    <Sparkles size={16} />
                    {Math.round(r.match * 100)}% совпадение
                  </div>
                  <TaskTile task={r.task} />
                  <div className="recommendation-reasons">
                    {r.reasons.map((s, i) => (
                      <p key={i}>✓ {s}</p>
                    ))}
                    <div className="chips">
                      {r.matched_terms.map((s, i) => (
                        <span key={i} className="badge">
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <Empty title="Пока нет подходящих рекомендаций">
              <Link to="/catalog">
                Все задачи по-прежнему доступны в каталоге →
              </Link>
            </Empty>
          )}
        </>
      )}
    </>
  );
}
export function PublicTask() {
  const { id } = useParams();
  const { meta, role, teamId } = useSession();
  const [inspector, setInspector] = useState(false);
  const cache = useQueryClient();
  const task = useQuery({
    queryKey: ["public-task", Number(id)],
    queryFn: () => api.publicTask(Number(id)),
  });
  const [idea, setIdea] = useState("");
  const [plan, setPlan] = useState("");
  const [timeline, setTimeline] = useState("");
  const [url, setUrl] = useState("");
  const proposal = useMutation({
    mutationFn: () =>
      api.propose(Number(id), {
        team_id: teamId,
        idea: idea.trim(),
        plan: plan.trim(),
        timeline: timeline.trim(),
        prototype_url: url.trim() || null,
      }),
    onSuccess: () => {
      toast.success("Отклик отправлен бизнесу");
      setIdea("");
      setPlan("");
      setTimeline("");
      setUrl("");
      void cache.invalidateQueries();
    },
  });
  if (task.isPending) return <Loading />;
  if (task.isError)
    return <ErrorState error={task.error} retry={() => void task.refetch()} />;
  const t = task.data;
  return (
    <>
      <Link className="back-link" to="/catalog">
        <ArrowLeft size={15} />
        Назад в каталог
      </Link>
      <PageHeading
        eyebrow={`${t.business_name} · ${meta.topics.find((x) => x.key === t.topic)?.label || "Без темы"}`}
        title={t.title}
        action={
          <Button variant="secondary" onClick={() => setInspector(true)}>
            <CircleHelp size={16} />
            Как это работает
          </Button>
        }
      >
        {t.proposals_count} откликов · Все опубликованные поля подтверждены
        бизнесом
      </PageHeading>
      <div className="builder-layout">
        <div className="panel">
          {meta.fields
            .filter((f) => f.key !== "title" && t.card[f.key])
            .map((f) => (
              <section className="public-field" key={f.key}>
                <h3>{f.label}</h3>
                <p>{t.card[f.key]}</p>
              </section>
            ))}
          {role === "team" && (
            <form
              className="proposal-form"
              onSubmit={(e) => {
                e.preventDefault();
                if (url && !/^https?:\/\//i.test(url.trim())) {
                  toast.error(
                    "Ссылка должна начинаться с http:// или https://",
                  );
                  return;
                }
                proposal.mutate();
              }}
            >
              <h2>Предложите своё решение</h2>
              <p className="muted">
                Расскажите, как ваша команда подойдёт к задаче.
              </p>
              <label htmlFor="idea">Идея · от 20 символов</label>
              <textarea
                id="idea"
                value={idea}
                onChange={(e) => setIdea(e.target.value)}
                minLength={20}
                maxLength={3000}
                required
                rows={3}
              />
              <label htmlFor="plan">План · от 20 символов</label>
              <textarea
                id="plan"
                value={plan}
                onChange={(e) => setPlan(e.target.value)}
                minLength={20}
                maxLength={3000}
                required
                rows={4}
              />
              <div className="form-grid">
                <div>
                  <label htmlFor="timeline">Срок</label>
                  <input
                    id="timeline"
                    value={timeline}
                    onChange={(e) => setTimeline(e.target.value)}
                    maxLength={200}
                    required
                    placeholder="Например, 6 недель"
                  />
                </div>
                <div>
                  <label htmlFor="prototype">
                    Ссылка на прототип · необязательно
                  </label>
                  <input
                    id="prototype"
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://…"
                  />
                </div>
              </div>
              <Button
                type="submit"
                disabled={
                  proposal.isPending ||
                  idea.trim().length < 20 ||
                  plan.trim().length < 20 ||
                  !timeline.trim()
                }
              >
                <Send size={16} />
                {proposal.isPending ? "Отправляем…" : "Отправить отклик"}
              </Button>
              {proposal.isError && <ErrorState error={proposal.error} />}
              {proposal.isSuccess && (
                <p className="success-text">
                  Отклик отправлен. <Link to="/proposals">Мои отклики →</Link>
                </p>
              )}
              <p className="muted small">
                Решение принимает только бизнес. Система не назначает команды.
              </p>
            </form>
          )}
        </div>
        <RatingPanel
          rating={t.rating}
          taskId={t.id}
          position={t.position}
          readOnly
        />
      </div>
      <Inspector taskId={t.id} open={inspector} onOpenChange={setInspector} />
    </>
  );
}

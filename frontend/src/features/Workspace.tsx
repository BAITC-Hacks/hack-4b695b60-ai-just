import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { ArrowRight, Check, Plus, Trophy } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/api/client";
import type { Proposal } from "@/api/types";
import { useSession } from "@/lib/session";
import { Button } from "@/components/ui/button";
import {
  Empty,
  ErrorState,
  LevelBadge,
  Loading,
  PageHeading,
  SafeLink,
} from "@/components/shared";
const statusLabels = {
  submitted: "На рассмотрении",
  selected: "Выбрана",
  rejected: "Отклонена",
};
export function MyTasks() {
  const { businessId } = useSession();
  const query = useQuery({
    queryKey: ["my-tasks", businessId],
    queryFn: () => api.tasks(businessId),
  });
  return (
    <>
      <PageHeading
        eyebrow="КАБИНЕТ БИЗНЕСА"
        title="Мои задачи"
        action={
          <Button asChild>
            <Link to="/builder">
              <Plus size={17} />
              Новая задача
            </Link>
          </Button>
        }
      >
        От первой идеи до совместного результата.
      </PageHeading>
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <ErrorState error={query.error} retry={() => void query.refetch()} />
      ) : query.data.length ? (
        <div className="my-task-list">
          {query.data.map((t) => (
            <div className="my-task-row" key={t.id}>
              <span className={`mini-score score-${t.level.key}`}>
                {t.score}
              </span>
              <div className="grow">
                <Link className="task-title-link" to={`/builder/${t.id}`}>
                  {t.title || "Новая задача"}
                </Link>
                <p className="muted">
                  {t.status === "published"
                    ? "Опубликована"
                    : t.status === "review"
                      ? "На проверке"
                      : "Уточнение"}{" "}
                  · <LevelBadge level={t.level} />
                </p>
              </div>
              <Button variant="secondary" asChild>
                <Link to={`/tasks/${t.id}/proposals`}>
                  Отклики ({t.proposals_count})<ArrowRight size={15} />
                </Link>
              </Button>
            </div>
          ))}
        </div>
      ) : (
        <Empty title="Здесь будут ваши задачи">
          <p>Начните с проблемы, которую хотите решить.</p>
          <Button asChild>
            <Link to="/builder">Создать первую задачу</Link>
          </Button>
        </Empty>
      )}
    </>
  );
}
export function Proposals({ business = false }: { business?: boolean }) {
  const { id } = useParams();
  const { businessId, teamId } = useSession();
  const query = useQuery({
    queryKey: ["proposals", business, id, businessId, teamId],
    queryFn: () =>
      business
        ? api.proposals(Number(id), businessId)
        : api.teamProposals(teamId),
  });
  return (
    <>
      <PageHeading
        eyebrow={business ? "КАБИНЕТ БИЗНЕСА" : "КАБИНЕТ КОМАНДЫ"}
        title={business ? `Отклики на задачу #${id}` : "Мои отклики"}
      >
        Решение принимает только бизнес. Система не назначает команды.
      </PageHeading>
      {business && (
        <Link className="back-link" to="/my-tasks">
          ← Мои задачи
        </Link>
      )}
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <ErrorState error={query.error} retry={() => void query.refetch()} />
      ) : query.data.length ? (
        <div className="proposal-list">
          {query.data.map((p) => (
            <ProposalCard key={p.id} proposal={p} business={business} />
          ))}
        </div>
      ) : (
        <Empty title="Откликов пока нет">
          {business ? (
            "Команды смогут откликнуться после публикации задачи."
          ) : (
            <Link to="/catalog">Найдите свою задачу в каталоге →</Link>
          )}
        </Empty>
      )}
    </>
  );
}
function ProposalCard({
  proposal: p,
  business,
}: {
  proposal: Proposal;
  business: boolean;
}) {
  const { businessId } = useSession();
  const cache = useQueryClient();
  const [comment, setComment] = useState(p.business_comment || "");
  const [title, setTitle] = useState("");
  const [points, setPoints] = useState(10);
  const change = useMutation({
    mutationFn: (fn: () => Promise<unknown>) => fn(),
    onSuccess: () => {
      void cache.invalidateQueries();
    },
    onError: (e) => toast.error(e.message),
  });
  return (
    <article className="panel proposal-card">
      <div className="row between">
        <div>
          <h2>{business ? p.team.name : p.task.title}</h2>
          <div className="chips">
            {p.team.skills.map((s) => (
              <span className="badge" key={s}>
                {s}
              </span>
            ))}
          </div>
        </div>
        <span className={`badge proposal-${p.status}`}>
          {statusLabels[p.status]}
        </span>
      </div>
      <h4>Идея</h4>
      <p>{p.idea}</p>
      <h4>План</h4>
      <p className="preserve-lines">{p.plan}</p>
      <div className="row between">
        <p>
          <b>Срок:</b> {p.timeline}
        </p>
        {p.prototype_url && <SafeLink url={p.prototype_url} />}
      </div>
      <div className="completeness">
        {[
          ["Идея", !!p.idea],
          ["План", !!p.plan],
          ["Срок", !!p.timeline],
          ["Прототип", !!p.prototype_url],
        ].map(([label, yes]) => (
          <span key={String(label)}>
            {yes ? "✓" : "○"} {label}
          </span>
        ))}
      </div>
      {business ? (
        <div className="decision">
          <label htmlFor={`comment-${p.id}`}>Комментарий · необязательно</label>
          <input
            id={`comment-${p.id}`}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            maxLength={2000}
          />
          <div className="row">
            <Button
              disabled={change.isPending || p.status === "selected"}
              onClick={() =>
                change.mutate(() =>
                  api
                    .decision(p.id, businessId, "selected", comment)
                    .then((r) => {
                      toast.success(`Команда ${p.team.name} выбрана`);
                      return r;
                    }),
                )
              }
            >
              <Check size={15} />
              Выбрать
            </Button>
            <Button
              variant="secondary"
              disabled={change.isPending || p.status === "rejected"}
              onClick={() =>
                change.mutate(() =>
                  api
                    .decision(p.id, businessId, "rejected", comment)
                    .then((r) => {
                      toast.success("Решение сохранено");
                      return r;
                    }),
                )
              }
            >
              Отклонить
            </Button>
          </div>
        </div>
      ) : (
        p.business_comment && (
          <blockquote>Комментарий бизнеса: {p.business_comment}</blockquote>
        )
      )}
      {(p.status === "selected" || p.milestones.length > 0) && (
        <div className="milestones">
          <h3>Этапы работы</h3>
          {p.milestones.map((m) => (
            <div className="milestone" key={m.id}>
              <span>
                {m.status === "confirmed" ? "✓" : "○"} {m.title}
              </span>
              <b>+{m.points}</b>
              {business &&
                m.status === "pending" &&
                p.status === "selected" && (
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={change.isPending}
                    onClick={() =>
                      change.mutate(() =>
                        api.confirmMilestone(m.id, businessId).then((r) => {
                          toast.success(
                            `+${r.milestone.points} баллов команде ${r.team.name}`,
                          );
                          return r;
                        }),
                      )
                    }
                  >
                    Подтвердить
                  </Button>
                )}
              {m.status === "confirmed" && (
                <small className="success-text">Подтверждён</small>
              )}
            </div>
          ))}
          {business && p.status === "selected" && (
            <form
              className="milestone-form"
              onSubmit={(e) => {
                e.preventDefault();
                change.mutate(() =>
                  api
                    .milestone(p.id, businessId, title.trim(), points)
                    .then((r) => {
                      setTitle("");
                      toast.success("Этап добавлен");
                      return r;
                    }),
                );
              }}
            >
              <div>
                <label htmlFor={`milestone-${p.id}`}>Название этапа</label>
                <input
                  id={`milestone-${p.id}`}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                  maxLength={200}
                  placeholder="Например, прототип бота"
                />
              </div>
              <div>
                <label htmlFor={`points-${p.id}`}>Баллы</label>
                <input
                  id={`points-${p.id}`}
                  type="number"
                  min={5}
                  max={30}
                  step={1}
                  value={points}
                  onChange={(e) => setPoints(Number(e.target.value))}
                  required
                />
              </div>
              <Button
                type="submit"
                variant="secondary"
                disabled={change.isPending || !title.trim()}
              >
                <Plus size={15} />
                Добавить
              </Button>
            </form>
          )}
        </div>
      )}
      {change.isError && (
        <p className="error-text" role="alert">
          {change.error.message}
        </p>
      )}
    </article>
  );
}
export function Leaderboard() {
  const query = useQuery({
    queryKey: ["leaderboard"],
    queryFn: api.leaderboard,
  });
  return (
    <>
      <PageHeading
        eyebrow="ПРОГРЕСС, КОТОРЫЙ ВИДНО"
        title="Команды, которые делают"
      >
        Баллы за реальные этапы, подтверждённые бизнесом. Каждый шаг имеет
        значение.
      </PageHeading>
      <div className="leaderboard-banner">
        <Trophy size={44} />
        <div>
          <h2>От первого прототипа — к результату</h2>
          <p>
            Отклик — начало пути. Баллы появляются, когда бизнес подтверждает
            выполненный этап.
          </p>
        </div>
      </div>
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <ErrorState error={query.error} retry={() => void query.refetch()} />
      ) : query.data.items.length ? (
        <div className="leaderboard">
          <div className="leader-row leader-head">
            <span>МЕСТО</span>
            <span>КОМАНДА</span>
            <span>ЭТАПЫ</span>
            <span>БАЛЛЫ</span>
          </div>
          {query.data.items.map(({ rank, team, confirmed_milestones }) => (
            <div
              className={`leader-row ${rank === 1 && team.progress_points > 0 ? "first" : ""}`}
              key={team.id}
            >
              <b className="rank">{String(rank).padStart(2, "0")}</b>
              <div>
                <h3>{team.name}</h3>
                <p className="muted">{team.skills.join(" · ")}</p>
              </div>
              <span>{confirmed_milestones} подтверждено</span>
              <strong className="leader-points">{team.progress_points}</strong>
            </div>
          ))}
        </div>
      ) : (
        <Empty title="Команд пока нет" />
      )}
    </>
  );
}

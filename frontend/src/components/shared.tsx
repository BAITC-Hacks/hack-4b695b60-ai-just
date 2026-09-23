import { AlertCircle, ArrowUpRight, Inbox, LoaderCircle } from "lucide-react";
import { Link } from "react-router";
import type { ReactNode } from "react";
import type { CatalogItem, Level } from "@/api/types";
import { useSession } from "@/lib/session";
import { Button } from "./ui/button";
export function Loading({ label = "Загружаем данные…" }: { label?: string }) {
  return (
    <div className="loading" role="status">
      <LoaderCircle className="spin" size={23} />
      <p>{label}</p>
      <div className="skeleton" />
      <div className="skeleton short" />
    </div>
  );
}
export function ErrorState({
  error,
  retry,
}: {
  error: Error | null;
  retry?: () => void;
}) {
  return (
    <div className="error-box" role="alert">
      <AlertCircle size={22} />
      <div>
        <strong>Не получилось загрузить данные</strong>
        <p>{error?.message || "Попробуйте ещё раз."}</p>
        {retry && (
          <Button variant="secondary" onClick={retry}>
            Повторить
          </Button>
        )}
      </div>
    </div>
  );
}
export function Empty({
  title = "Пока ничего нет",
  children,
}: {
  title?: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <Inbox size={34} />
      <h3>{title}</h3>
      <div className="muted">{children}</div>
    </div>
  );
}
export function PageHeading({
  eyebrow,
  title,
  children,
  action,
}: {
  eyebrow?: string;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {children && <p className="muted">{children}</p>}
      </div>
      {action}
    </div>
  );
}
export function LevelBadge({ level }: { level: Level }) {
  return (
    <span className={`badge level-${level.key}`}>
      <span className="dot" />
      {level.label}
    </span>
  );
}
export function TaskTile({ task }: { task: CatalogItem }) {
  const { meta } = useSession();
  return (
    <Link
      className={`task-tile ${task.highlighted ? "highlighted" : ""} ${task.needs_clarification ? "needs-clarification" : ""}`}
      to={`/catalog/${task.id}`}
    >
      <div className="row between">
        <span className="topic">
          {meta.topics.find((t) => t.key === task.topic)?.label || "Без темы"}
        </span>
        <span className="catalog-number">№{task.position} в каталоге</span>
      </div>
      <h3>{task.title}</h3>
      <p className="business-name">{task.business_name}</p>
      <p className="task-preview">
        {task.need_preview || "Потребность ещё не описана."}
      </p>
      {task.needs_clarification && (
        <span className="badge">Требует уточнения</span>
      )}
      <div className="tile-footer">
        <LevelBadge level={task.level} />
        <span className={`tile-score score-${task.level.key}`}>
          {task.score}
          <small>/100</small>
        </span>
      </div>
      <div className="row between tile-bottom">
        <span>{task.proposals_count} откликов</span>
        <ArrowUpRight size={18} />
      </div>
    </Link>
  );
}
export function SafeLink({ url }: { url: string }) {
  let safe = false;
  try {
    const parsed = new URL(url);
    safe = parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    /* Invalid links are rendered as text. */
  }
  return safe ? (
    <a href={url} target="_blank" rel="noopener noreferrer">
      Открыть прототип ↗
    </a>
  ) : (
    <span className="muted">Некорректная ссылка</span>
  );
}

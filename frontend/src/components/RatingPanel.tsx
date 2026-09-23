import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { animate, motion, useReducedMotion } from "motion/react";
import { toast } from "sonner";
import { Award, Check, ChevronRight, Sparkles, TrendingUp } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { FieldKey, Rating } from "@/api/types";
import { Button } from "./ui/button";
import { LevelBadge } from "./shared";
const RatingHistoryChart = lazy(() => import("./RatingHistoryChart"));

export function RatingPanel({
  rating,
  taskId,
  position,
  onConfirm,
  onFocus,
  busy = false,
  readOnly = false,
}: {
  rating: Rating;
  taskId: number;
  position?: number | null;
  onConfirm?: () => void;
  onFocus?: (field: FieldKey) => void;
  busy?: boolean;
  readOnly?: boolean;
}) {
  const [display, setDisplay] = useState(rating.score);
  const previous = useRef(rating);
  const reduceMotion = useReducedMotion();
  const history = useQuery({
    queryKey: ["history", taskId],
    queryFn: () => api.history(taskId),
    enabled: !readOnly,
  });
  useEffect(() => {
    const controls = animate(previous.current.score, rating.score, {
      duration: reduceMotion ? 0 : 0.65,
      onUpdate: (v) => setDisplay(Math.round(v)),
    });
    if (!readOnly) {
      rating.achievements
        .filter(
          (a) =>
            a.earned &&
            !previous.current.achievements.find((x) => x.key === a.key)?.earned,
        )
        .forEach((a) => toast.success(`Достижение: ${a.label}`));
      if (
        rating.level.key === "priority" &&
        previous.current.level.key !== "priority" &&
        !reduceMotion
      )
        void import("canvas-confetti")
          .then(({ default: confetti }) =>
            confetti({
              particleCount: 85,
              spread: 70,
              origin: { y: 0.7 },
              disableForReducedMotion: true,
            }),
          )
          .catch(() => undefined);
    }
    previous.current = rating;
    return () => controls.stop();
  }, [rating, readOnly, reduceMotion]);
  return (
    <aside className={`rating-panel level-border-${rating.level.key}`}>
      <div className="row between">
        <h3>Готовность задачи</h3>
        <TrendingUp size={19} />
      </div>
      <div className={`score-ring score-${rating.level.key}`}>
        <svg viewBox="0 0 160 160" aria-hidden="true">
          <circle
            cx="80"
            cy="80"
            r="68"
            fill="none"
            stroke="var(--line)"
            strokeWidth="9"
          />
          <motion.circle
            cx="80"
            cy="80"
            r="68"
            fill="none"
            stroke="currentColor"
            strokeWidth="9"
            strokeLinecap="round"
            strokeDasharray="427.26"
            animate={{ strokeDashoffset: 427.26 * (1 - rating.score / 100) }}
            initial={false}
            transition={{ duration: reduceMotion ? 0 : 0.7 }}
            transform="rotate(-90 80 80)"
          />
        </svg>
        <div>
          <strong>{display}</strong>
          <span>из 100 баллов</span>
        </div>
        {rating.delta !== 0 && !readOnly && (
          <motion.b
            className="score-delta"
            role="status"
            aria-live="polite"
            key={`${rating.score}-${rating.delta}`}
            initial={reduceMotion ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {rating.delta > 0 ? "+" : ""}
            {rating.delta}
          </motion.b>
        )}
      </div>
      <div className="center">
        <LevelBadge level={rating.level} />
      </div>
      <p className="rating-next">
        {rating.next_level
          ? `До «${rating.next_level.label}» — ${rating.next_level.points_needed} баллов`
          : "Задача полностью готова к работе"}
      </p>
      <progress
        max="100"
        value={rating.score}
        aria-label={`Готовность задачи: ${rating.score} из 100`}
      />
      {onConfirm && rating.potential_score > rating.score && (
        <div className="potential">
          <Sparkles size={17} />
          <div>
            <b>AI нашёл ещё +{rating.potential_score - rating.score}</b>
            <p>Подтвердите предложенные поля</p>
            <Button
              size="sm"
              variant="secondary"
              onClick={onConfirm}
              disabled={busy}
            >
              Подтвердить всё
            </Button>
          </div>
        </div>
      )}
      {position && (
        <div className="position">
          <span>
            {readOnly ? "Место в каталоге" : "Если опубликовать сейчас"}
          </span>
          <b>
            №{position} <TrendingUp size={15} />
          </b>
        </div>
      )}
      <section>
        <h4>Из чего складывается рейтинг</h4>
        {rating.breakdown.map((c) => (
          <details className="criterion" key={c.criterion}>
            <summary>
              <span>{c.label}</span>
              <b>
                {c.earned}
                <small>/{c.max}</small>
              </b>
            </summary>
            <ul>
              {c.checks.map((ch) => (
                <li key={ch.id} className={ch.passed ? "passed" : ""}>
                  {ch.passed ? (
                    <Check size={13} />
                  ) : (
                    <span className="empty-check" />
                  )}
                  <span>{ch.label}</span>
                  <b>{ch.points}</b>
                </li>
              ))}
            </ul>
          </details>
        ))}
      </section>
      {!readOnly && rating.missing.length > 0 && (
        <section>
          <h4>Что поднимет рейтинг</h4>
          {rating.missing.slice(0, 3).map((m) => (
            <button
              className="hint-button"
              key={m.check_id}
              onClick={() => onFocus?.(m.field)}
            >
              <b>+{m.points_gain}</b>
              <span>{m.hint}</span>
              <ChevronRight size={15} />
            </button>
          ))}
        </section>
      )}
      <section>
        <h4>Ваши достижения</h4>
        <div className="achievements">
          {rating.achievements.map((a) => (
            <div
              key={a.key}
              className={a.earned ? "achievement earned" : "achievement"}
              title={`${a.label}: ${a.description}`}
            >
              <Award size={20} />
              <span>{a.label}</span>
            </div>
          ))}
        </div>
      </section>
      {!readOnly && (
        <section>
          <h4>История готовности</h4>
          {history.isPending ? (
            <p className="muted">Загружаем историю…</p>
          ) : history.isError ? (
            <button
              className="text-link"
              onClick={() => void history.refetch()}
            >
              Повторить загрузку истории
            </button>
          ) : history.data.length ? (
            <>
              <Suspense
                fallback={
                  <div
                    className="history-chart"
                    aria-label="Загружаем график…"
                  />
                }
              >
                <RatingHistoryChart history={history.data} />
              </Suspense>
              <p className="history-numbers">
                {history.data.map((h) => h.score).join(" → ")}
              </p>
            </>
          ) : (
            <p className="muted">История появится после первого изменения.</p>
          )}
        </section>
      )}
      <p className="rating-note">
        Баллы начисляют прозрачные правила.
        <br />
        AI не оценивает и не выбирает команды.
      </p>
    </aside>
  );
}

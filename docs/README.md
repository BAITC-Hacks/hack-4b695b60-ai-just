# Документация

| Документ | О чём | Кому |
| --- | --- | --- |
| [hackathon-brief.md](hackathon-brief.md) | Кейс, критерии оценки, требования к AI, правила площадки, безопасность, ресурсы OpenAI и NVIDIA, сдача | Обоим, первым делом |
| [architecture.md](architecture.md) | Компоненты, стек, структура репозитория, модель данных, состояния, потоки, `.env` | A; B — разделы 1–3 |
| [api-contract.md](api-contract.md) | Типы и эндпоинты: договор между backend и frontend | Обоим |
| [rating-and-gamification.md](rating-and-gamification.md) | Формула рейтинга (18 проверок), уровни, правила каталога и рекомендаций, механики геймификации | Обоим |
| [ai-ml.md](ai-ml.md) | Провайдеры и модели, промпты, контракты, grounding, заглушка, рекомендации, eval | A |
| [nvidia-brev.md](nvidia-brev.md) | Своя модель на GPU NVIDIA Brev: пошагово | A |
| [plan-5h.md](plan-5h.md) | Таймлайн двух дорожек, синхронизации, git-процесс, cut-list, риски | Обоим |
| [demo-script.md](demo-script.md) | Сценарий демо на 5 минут, готовые тексты, запасные планы, ответы жюри | Обоим, B ведёт |
| [team/A-backend-ml.md](team/A-backend-ml.md) | Роль A: backend и ML через Cursor и Codex, промпты по фазам | A |
| [team/B-frontend-product.md](team/B-frontend-product.md) | Роль B: frontend, UX геймификации, демо, промпты по фазам | B |
| [team/B-ui-polish.md](team/B-ui-polish.md) | ТЗ на полировку интерфейса: темы, языки RU/KZ/EN, анимации, чек-лист качества | B |

**Порядок чтения для A:** hackathon-brief → plan-5h → team/A-backend-ml → architecture → api-contract → rating-and-gamification → ai-ml → nvidia-brev.

**Порядок чтения для B:** hackathon-brief → plan-5h → team/B-frontend-product → api-contract → rating-and-gamification (разделы 4, 7, 10) → demo-script.

Правило: если меняется поведение, в том же изменении обновляем документ.

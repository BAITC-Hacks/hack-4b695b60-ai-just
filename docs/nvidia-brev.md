# NVIDIA: Build API и Brev

От NVIDIA организаторы дают две вещи. Используем обе, но **ни одна не стоит на критическом пути**: если что-то не поднялось, сценарий работает через OpenAI или офлайн.

| Что | Что это | Зачем нам | Приоритет |
| --- | --- | --- | :-: |
| **NVIDIA Build** (build.nvidia.com) | Hosted NIM API: модели NVIDIA по ключу, OpenAI-совместимо, без своего GPU | Второй LLM-провайдер (Nemotron 3) и основные эмбеддинги (`nemotron-3-embed-1b`) | P1 |
| **NVIDIA Brev** (brev.nvidia.com) | Облачные GPU-инстансы (L40S, A100, H100 и другие) по кредитам, плюс Launchables — готовые окружения в один клик | Своя модель: приватный режим, в котором черновики бизнеса не уходят третьим лицам; прогон eval | P2 |

История для жюри: «У нас три уровня AI. Облачный OpenAI для качества на русском. NVIDIA Nemotron через Build API. Своя модель на GPU NVIDIA Brev для приватных данных. Всё переключается на лету, а офлайн-заглушка страхует всё остальное. Какую модель ставить первой, решили по метрикам eval».

## 1. Активация (из инструкции организаторов)

1. **Brev:** промоссылка → вход в аккаунт NVIDIA (при запросе создать NVIDIA Cloud Account) → Billing → **Redeem Code** → проверить Current Balance.
2. **Build:** build.nvidia.com/settings/api-keys → тот же аккаунт → **Generate API Key** (название и срок действия) → сохранить ключ `nvapi-...`.
3. Ключ записать только в `.env` в корне: `NVIDIA_API_KEY=nvapi-...`. Не коммитить, не присылать в чаты, не вставлять в код и во frontend.

## 2. NVIDIA Build: проверка за 1 минуту

PowerShell:

```powershell
$env:NVIDIA_API_KEY = "nvapi-..."   # только в этой сессии терминала, не в файлы
$h = @{ Authorization = "Bearer $env:NVIDIA_API_KEY"; "Content-Type" = "application/json" }
$body = @{
  model = "nvidia/nemotron-3-nano-30b-a3b"
  messages = @(@{ role = "user"; content = "Ответь одним словом: столица Казахстана?" })
  max_tokens = 50
  chat_template_kwargs = @{ enable_thinking = $false }
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "https://integrate.api.nvidia.com/v1/chat/completions" -Method Post -Headers $h -Body $body
```

Python — так же, как в backend:

```python
from openai import OpenAI

client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=NVIDIA_API_KEY)
resp = client.chat.completions.create(
    model="nvidia/nemotron-3-nano-30b-a3b",
    messages=[{"role": "user", "content": "Верни JSON {\"ok\": true}"}],
    response_format={"type": "json_object"},
    temperature=0.2,
    max_tokens=512,
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)
emb = client.embeddings.create(
    model="nvidia/nemotron-3-embed-1b",
    input=["Telegram-бот для ответов о статусе доставки"],
    encoding_format="float",
    extra_body={"input_type": "passage", "truncate": "END"},
)
```

Модели и параметры:
- LLM: `nvidia/nemotron-3-nano-30b-a3b` — быстрая, по умолчанию. `nvidia/nemotron-3-super-120b-a12b` — качественнее, для eval.
- У Nemotron 3 рассуждение включено по умолчанию. Для JSON отключаем: `chat_template_kwargs.enable_thinking=false`. Иначе ответ медленнее и может содержать блок рассуждений.
- Эмбеддинги: `nvidia/nemotron-3-embed-1b` с обязательным `input_type`: `passage` для задач, `query` для профиля команды. Старый `llama-3.2-nv-embedqa-1b-v2` на Build помечен как устаревший.
- Точные ID и доступность моделей смотрим на build.nvidia.com/models. Все ID задаются в `.env`.

## 3. NVIDIA Brev: своя модель на GPU

### 3.1 План по времени

| Когда | Что | Кто |
| --- | --- | --- |
| T+0:10 | Создать инстанс в консоли и запустить модель командой из раздела 3.4. Дальше она грузится в фоне | A (руками, 5 минут) |
| T+1:00 | Проверить `/v1/models`, подключить провайдер `brev` | A2 (Codex) |
| T+2:00 | Прогнать eval с `--providers brev` | A2 |
| **T+2:30** | **Не отвечает — бросаем Brev**, остаётся NVIDIA Build | A |
| После демо | **Остановить или удалить инстанс** | A |

### 3.2 Создание инстанса: веб-консоль (основной путь для Windows)

1. brev.nvidia.com → **Create Instance** (или **New**).
2. Режим **VM Mode**: VM с Python, CUDA и Docker. Не Container Mode.
3. GPU:
   - **L40S 48GB** — хватит для Nemotron 3 Nano в FP8 или для 8–9B-моделей в BF16;
   - **A100 80GB или H100 80GB** — для Nemotron 3 Nano в BF16 (веса около 60 GB);
   - смотрим цену за час и остаток кредитов.
4. Имя: `challenge-hub-llm` → **Deploy**. Подготовка занимает несколько минут.
5. Во вкладке **Access** будут способы подключения: браузерный терминал, SSH, туннели.

Альтернатива — **Launchables** (Explore): готовые окружения с NIM или vLLM в один клик. Если есть подходящий под Nemotron, это быстрее.

### 3.3 Brev CLI в WSL (для port-forward)

На машине A есть WSL с Ubuntu. Нативного CLI для Windows нет, Brev работает через WSL.

```bash
# в Ubuntu (WSL)
curl -fsSL https://raw.githubusercontent.com/brevdev/brev-cli/main/bin/install-latest.sh | bash
export PATH="$HOME/.local/bin:$PATH"   # и добавить эту строку в ~/.bashrc
brev --version
brev login                              # откроет браузер
brev refresh && brev ls                 # увидеть инстанс, созданный в консоли
# или создать из CLI (строку типа GPU взять из каталога GPU Types в доках Brev):
# brev create challenge-hub-llm --gpu "nebius.l40sx1.pcie"
brev shell challenge-hub-llm
```

### 3.4 Запуск модели на инстансе

Сначала проверяем GPU: `nvidia-smi`.

**Вариант A: vLLM с весами Hugging Face (рекомендуем).**

```bash
export BREV_LLM_API_KEY=$(openssl rand -hex 16); echo "$BREV_LLM_API_KEY"   # сохранить в .env на ноутбуке
docker run -d --name nemotron --gpus all --ipc=host -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  --model nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8 \
  --served-model-name nemotron-3-nano \
  --max-model-len 32768 \
  --trust-remote-code \
  --api-key "$BREV_LLM_API_KEY"
docker logs -f nemotron        # ждём "Application startup complete"
curl -s localhost:8000/v1/models -H "Authorization: Bearer $BREV_LLM_API_KEY"
```

- На A100 или H100 80GB можно брать BF16: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16`.
- Точное имя репозитория сверить на huggingface.co/nvidia. Если модель не влезает или не стартует, берём модель поменьше (8–9B), это та же команда с другим `--model`.
- Рассуждение отключаем в запросе: `extra_body={"chat_template_kwargs": {"enable_thinking": False}}`. JSON-режим: `response_format={"type": "json_schema", ...}`.
- Скрипт с этой командой — `infra/brev/serve_vllm.sh`.

**Вариант B: NVIDIA NIM (контейнер из NGC).**

```bash
# NGC_API_KEY — ключ NGC; ключ с build.nvidia.com обычно тоже подходит для nvcr.io, иначе выпустить на ngc.nvidia.com
echo "$NGC_API_KEY" | docker login nvcr.io -u '$oauthtoken' --password-stdin
mkdir -p ~/.cache/nim
docker run -d --name nim --gpus all --shm-size=16GB -e NGC_API_KEY \
  -v ~/.cache/nim:/opt/nim/.cache -p 8000:8000 \
  <образ NIM со страницы модели на build.nvidia.com, вкладка Deploy → Docker>
```

- Проверенный пример из документации Brev — `nvcr.io/nim/meta/llama-3.1-8b-instruct` (влезает в L40S), но по-русски он слабее.
- В NIM строгий JSON включается через `extra_body={"nvext": {"guided_json": schema}}`.
- Скрипт — `infra/brev/serve_nim.sh`.

### 3.5 Доступ с ноутбука

| Способ | Как | Подходит для API из backend? |
| --- | --- | --- |
| **Port-forward** (рекомендуем) | В WSL: `brev port-forward challenge-hub-llm --port 8001:8000` | Да. С Windows доступно на `http://localhost:8001/v1`: WSL2 по умолчанию пробрасывает localhost. Если нет, запускаем backend внутри WSL |
| Туннель из консоли (Access → Using Tunnels) | Публичный HTTPS URL через Cloudflare | **Нет**: при первом входе нужна авторизация в браузере, запросы из кода получат HTML-страницу логина |
| Открытый порт (Port Exposure) | Открыть порт 8000 **только для своего IP** | Запасной вариант. Обязательно с `--api-key`; не открывать на весь интернет |

`.env` на ноутбуке:

```dotenv
BREV_LLM_BASE_URL=http://localhost:8001/v1
BREV_LLM_MODEL=nemotron-3-nano
BREV_LLM_API_KEY=<ключ, который сгенерировали на инстансе>
```

Проверка: `curl http://localhost:8001/v1/models -H "Authorization: Bearer <ключ>"`, затем `GET /api/health`: провайдер `brev` должен быть `available: true`.

### 3.6 Использование в приложении

- На демо включить приватный режим: `PUT /api/ai/provider {"mode": "brev"}` или переключатель в UI. AI Inspector покажет `provider: brev, model: nemotron-3-nano`.
- Eval: `uv run python -m eval.run_eval --providers brev,nvidia,openai,stub`.

### 3.7 Деньги и безопасность

- **Инстанс тарифицируется, пока запущен.** После демо: `brev stop challenge-hub-llm` (или Stop в консоли), после хакатона — `brev delete challenge-hub-llm`.
- Эндпоинт модели — только с `--api-key`. Не выставлять открытым на весь интернет.
- Ключи `NVIDIA_API_KEY`, `NGC_API_KEY`, `BREV_LLM_API_KEY` — только в `.env`. После хакатона удалить или отозвать (требование безопасности организаторов).
- Сеть площадки общая и недоверенная: не сканировать её и ничего на ней не поднимать наружу.

### 3.8 Если что-то пошло не так

| Симптом | Что делать |
| --- | --- |
| `CUDA out of memory` или контейнер падает | Уменьшить `--max-model-len` (16384), взять FP8 или модель меньше, взять GPU на 80GB |
| Долгий первый старт | Грузятся десятки гигабайт весов, это нормально. Поэтому стартуем в T+0:10 |
| `401 Unauthorized` | Не совпадает `BREV_LLM_API_KEY` в `.env` и на инстансе |
| Вместо JSON пришла HTML-страница | Используется туннель Cloudflare, переключиться на port-forward |
| vLLM не знает архитектуру модели | Обновить образ (`vllm/vllm-openai:latest`) или взять NIM или другую модель |
| К T+2:30 не работает | Бросаем. NVIDIA в проекте всё равно есть через Build API |

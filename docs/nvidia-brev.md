# NVIDIA Brev: своя модель на GPU

NVIDIA Build API в проекте не используется. Nemotron запускаем на своём GPU-инстансе Brev через vLLM. Если инстанс недоступен, AI работает через OpenAI или офлайн-заглушку; рекомендации переходят с OpenAI embeddings на TF-IDF.

## 1. Выбор окружения

1. Откройте **Compute → Create Environment**. Кредит виден в правом верхнем углу.
2. Выберите семейство **L40S**, 1 GPU и вариант с **48 GB VRAM**. Для Nemotron 3 Nano FP8 также нужны достаточная RAM и дисковое пространство для загрузки весов. Сравните цену за час, RAM и пометки **stop/start** и **flexible ports**. Если L40S недоступна, вариант с 80+ GB VRAM тоже подойдёт, но проверьте цену до запуска.
3. Выберите VM с Docker/CUDA и SSH или JupyterLab, задайте имя `challenge-hub-llm`, затем создайте окружение.
4. В разделе окружения откройте терминал и проверьте `nvidia-smi` и `docker --version`.

Инстанс тарифицируется во время работы. При кредите $50, например, цена $2.63/ч даёт менее 19 часов без учёта хранения и иных расходов. Остановите инстанс после проверки; если у провайдера нет stop/start, удалите его.

## 2. Запуск vLLM на инстансе

В терминале Brev выполните `infra/brev/serve_vllm.sh` после копирования скрипта на инстанс. Скрипт требует переменную `BREV_LLM_API_KEY`, которую нужно сгенерировать локально на инстансе:

```bash
export BREV_LLM_API_KEY="$(openssl rand -hex 24)"
bash serve_vllm.sh
docker logs -f challenge-hub-nemotron
curl -fsS http://localhost:8000/v1/models -H "Authorization: Bearer $BREV_LLM_API_KEY"
```

Сохраните ключ только в корневом `.env` проекта на ноутбуке. Скрипт использует `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8` из Hugging Face и OpenAI-совместимый сервер vLLM. При нехватке памяти уменьшите `--max-model-len` в скрипте или выберите меньшую модель и обновите `BREV_LLM_MODEL`.

## 3. Подключение к backend

Brev CLI устанавливается в Ubuntu/WSL на Windows:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/brevdev/brev-cli/main/bin/install-latest.sh)"
brev login
brev refresh
brev list
brev port-forward challenge-hub-llm --port 8001:8000
```

Туннель должен оставаться запущенным. В корневом `.env` проекта:

```dotenv
AI_PROVIDER_CHAIN=openai,brev,stub
BREV_LLM_BASE_URL=http://localhost:8001/v1
BREV_LLM_MODEL=nemotron-3-nano
BREV_LLM_API_KEY=<ключ с инстанса>
EMBED_PROVIDER_CHAIN=openai,tfidf
```

Проверка с ноутбука: `GET http://localhost:8001/v1/models` с заголовком `Authorization: Bearer <ключ>`. Затем `GET /api/health` должен показать `brev` как доступный провайдер. Для проверки только Brev используйте `PUT /api/ai/provider` с `{"mode":"brev"}` и создайте черновик; в AI Inspector смотрите фактически ответивший `provider`. Если сервер не отвечает, приложение перейдёт к `stub`.

Не открывайте порт модели в общий интернет. Браузерные туннели Brev с авторизацией не подходят для запросов backend.

## 4. Eval и завершение

Из папки `backend`: `uv run python -m eval.run_eval --providers stub,openai,brev`. В отчёте смотрите `provider_used`: отсутствие ключа или инстанса означает, что отвечала заглушка. После демо остановите или удалите инстанс через консоль Brev и отзовите временный ключ.

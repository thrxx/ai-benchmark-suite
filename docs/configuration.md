# Конфигурация и настройка

Проект использует файл `.env` для управления всеми параметрами запуска. 
При первом запуске `python launcher.py` автоматически создаёт и заполняет этот файл на основе вашего выбора. 
Однако вы можете редактировать его вручную для тонкой настройки или интеграции в CI/CD.

## 📂 Файл `.env`

Расположен в корне проекта. Структура:
```ini
PROVIDER=ollama
BENCHMARK_MODE=coding
MODEL_NAME=qwen2.5-coder-7b
API_BASE_URL=http://host.docker.internal:11434/api
API_TYPE=ollama
API_KEY=dummy
TIMEOUT_GEN=120
```

##  Описание переменных

| Переменная | Тип | По умолчанию | Описание |
|------------|-----|--------------|----------|
| `PROVIDER` | `lmstudio` / `ollama` | `ollama` | Бэкенд для инференса. Определяет формат API и логику сканирования моделей. |
| `BENCHMARK_MODE` | `coding` / `assistant` | `coding` | Набор тестовых задач. `coding` проверяет навыки программирования, `assistant` — логику, безопасность и креативность. |
| `MODEL_NAME` | `string` | `-` | Точное название модели, загруженной в провайдер. Должно совпадать с выводом `ollama list` или списком в LM Studio. |
| `API_BASE_URL` | `URL` | `-` | Адрес API **для Docker-контейнера**. Используйте `host.docker.internal` для доступа к локальному серверу с хоста. |
| `API_TYPE` | `ollama` / `openai_compat` | `ollama` | Протокол взаимодействия. `ollama` использует нативный `/api/generate`, `openai_compat` — совместимый `/v1/chat/completions`. |
| `API_KEY` | `string` | `dummy` | Ключ авторизации. Для локальных провайдеров не требуется, но некоторые клиенты ожидают непустое значение. |
| `TIMEOUT_GEN` | `int` (секунды) | `120` | Максимальное время ожидания ответа от модели на одну задачу. |

## ⚙️ Настройка под провайдеров

### Ollama
```ini
PROVIDER=ollama
API_BASE_URL=http://host.docker.internal:11434/api
API_TYPE=ollama
```
*Примечание:* Если у вас Ollama ≥ 0.1.30 и вы включили режим совместимости, можно использовать `API_TYPE=openai_compat` и URL `http://host.docker.internal:11434/v1`.

### LM Studio
```ini
PROVIDER=lmstudio
API_BASE_URL=http://host.docker.internal:1234/v1
API_TYPE=openai_compat
```
*Примечание:* Убедитесь, что в настройках LM Studio сервер слушает порт `1234` и включена опция "Enable Server".

##  Профили запуска

В зависимости от ваших целей, рекомендуем следующие конфигурации:

| Профиль | `.env` настройки | Когда использовать |
|---------|------------------|-------------------|
| ⚡ **Быстрый тест** | `MODEL_NAME=llama3.2`<br>`TIMEOUT_GEN=60` | Проверка пайплайна, отладка валидаторов, тест на CPU |
| 🧠 **Полный бенчмарк** | `MODEL_NAME=qwen2.5-coder-14b`<br>`TIMEOUT_GEN=300` | Оценка реальных возможностей модели, генерация отчётов |
|  **Production (GPU)** | `MODEL_NAME=deepseek-coder-6.7b`<br>`TIMEOUT_GEN=90`<br>`API_TYPE=openai_compat` | CI/CD, ежедневные прогоны, сервер с NVIDIA/AMD GPU |

##  Ручное переопределение (CLI)

Вы можете запустить бенчмарк без редактирования `.env`, передав переменные прямо в команду:

```bash
# Временный запуск с другой моделью и увеличенным таймаутом
MODEL_NAME=mistral TIMEOUT_GEN=180 python launcher.py

# Или через экспорт в оболочку (Linux/macOS)
export BENCHMARK_MODE=assistant
export MODEL_NAME=qwen2.5:7b
python launcher.py
```

## ✅ Проверка конфигурации

Перед запуском полного теста убедитесь, что настройки корректны:

```bash
# 1. Проверьте содержимое .env
cat .env

# 2. Убедитесь, что API отвечает
curl -s http://localhost:11434/api/tags | jq '.models[].name'  # Ollama
curl -s http://localhost:1234/v1/models | jq '.data[].id'      # LM Studio

# 3. Запустите лаунчер в режиме dry-run (если поддерживается) или просто выберите модель
python launcher.py
```

## ⚠️ Частые ошибки конфигурации

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `404 Model not found` | `MODEL_NAME` не совпадает с загруженной моделью | Проверьте точное название через `ollama list` или интерфейс LM Studio |
| `Connection refused` | Неверный `API_BASE_URL` или провайдер выключен | Используйте `host.docker.internal`, проверьте статус сервера |
| `ReadTimeout` | `TIMEOUT_GEN` слишком мал для размера модели | Увеличьте до `300` для 14B+ моделей или включите GPU offload |
| `Invalid API response` | Несовпадение `API_TYPE` и реального эндпоинта | Для Ollama используйте `ollama`, для LM Studio — `openai_compat` |

## 📖 Дальнейшие шаги
- [Описание задач бенчмарка](benchmarks.md)
- [Интерпретация результатов](results.md)
- [Безопасность и изоляция](../SECURITY.md)

---
# 🤖 AI Model Benchmark Suite

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI Lint](https://github.com/thrxx/ai-benchmark-suite/actions/workflows/lint.yml/badge.svg)](https://github.com/thrxx/ai-benchmark-suite/actions/workflows/lint.yml)
[![OS](https://img.shields.io/badge/OS-Windows%2011%20Pro-blue)](https://www.microsoft.com/windows)
[![Ollama](https://img.shields.io/badge/Ollama-latest-orange)](https://ollama.ai)
[![Docker](https://img.shields.io/badge/Docker-Desktop-blue)](https://www.docker.com/products/docker-desktop)

Профессиональный инструмент для автоматического бенчмарка локальных AI-моделей. Тестирует навыки программирования и ассистент-рассуждений через изолированные Docker-контейнеры с детальным анализом результатов.

## 🌟 Возможности

- **🧑‍ Coding Benchmark** — 10 задач: Python, JS, SQL, C++, Go, алгоритмы, рефакторинг, тестирование
- **🤖 Assistant Benchmark** — 10 задач: форматирование, логика, безопасность, креативность, многоязычие
- **🔄 Multi-Provider** — Поддержка LM Studio (OpenAI-compatible) и Ollama (native + v1 API)
- **🐳 Secure Sandbox** — Запуск сгенерированного кода в изолированном контейнере
- **📊 Smart Validation** — Динамическое исполнение, статический анализ, семантические проверки
- **🎯 Interactive Launcher** — Авто-сканирование моделей, выбор провайдера/режима/модели, генерация `.env`
- **📈 Weighted Scoring** — Взвешенная оценка по сложности (Easy/Medium/Hard) с actionable выводами

## 🚀 Быстрый старт

### Требования
- Python 3.9+
- Docker Desktop (Windows/macOS/Linux)
- Один из провайдеров: **LM Studio** ≥0.2.0 или **Ollama** ≥0.1.0

### Установка
```bash
git clone https://github.com/thrxx/ai-benchmark-suite.git
cd ai-benchmark-suite
pip install -r requirements.txt
```

### Запуск
```bash
python launcher.py
```
Интерактивный процесс:
1. 🌐 Выберите провайдера (`LM Studio` / `Ollama`)
2. 🎯 Выберите тип бенчмарка (`Coding` / `Assistant`)
3. 📦 Выберите модель из автоматически отсканированного списка
4. 🐳 Дождитесь завершения тестов в Docker-контейнере

## 📊 Пример результата

После завершения в папке `results/` появится `benchmark_result.json`:
```json
{
  "model": "qwen2.5-coder-7b",
  "mode": "coding",
  "provider": "ollama",
  "overall_score": 68.4,
  "breakdown": {
    "easy_avg": 86.2,
    "medium_avg": 61.5,
    "hard_avg": 42.0
  },
  "conclusion": "🟡 ХОРОШО (Требует мелких правок)\nПаттерны: Легкие=86.2% | Средние=61.5% | Сложные=42.0%\n⚠️ Слабое место: многопоточность/асинхронность/архитектура.\n✅ Рекомендация: подходит для daily-использования с code-review."
}
```

### Система оценки
| Диапазон | Оценка | Рекомендация |
|----------|--------|--------------|
| `90–100` | 🟢 ОТЛИЧНО | Production-ready, минимальный code-review |
| `75–89`  | 🟡 ХОРОШО | Надёжный ассистент, требует проверки сложных задач |
| `60–74`  | 🟠 СРЕДНЕ | Нужен рефакторинг промптов или RAG-контекст |
| `<60`    | 🔴 НИЗКО | Высокий риск галлюцинаций, требует доработки |

**Формула:** `Общий скор = Σ(скор_задачи × вес) / Σ(вес)`  
*(Лёгкие: ×1.0, Средние: ×1.5, Сложные: ×2.0)*

## ️ Конфигурация

Все параметры управляются через `.env` (генерируется автоматически, но можно редактировать вручную):
```env
PROVIDER=ollama
BENCHMARK_MODE=coding
MODEL_NAME=qwen2.5-coder-7b
API_BASE_URL=http://host.docker.internal:11434/api
API_TYPE=ollama
API_KEY=dummy
TIMEOUT_GEN=120
```

| Переменная | Описание |
|------------|----------|
| `PROVIDER` | `lmstudio` или `ollama` |
| `BENCHMARK_MODE` | `coding` или `assistant` |
| `MODEL_NAME` | Точное название модели в провайдере |
| `API_BASE_URL` | Адрес API **для контейнера** (`host.docker.internal`) |
| `API_TYPE` | `openai_compat` (LM Studio/Ollama v1) или `ollama` (native) |
| `TIMEOUT_GEN` | Лимит генерации в секундах (рекомендуется 120–300) |

## 📁 Структура проекта
```
ai-benchmark-suite/
├── launcher.py              # Интерактивный выбор провайдера/режима/модели
├── coding_benchmark.py      # Валидаторы для coding-задач
├── assistant_benchmark.py   # Валидаторы для assistant-задач
├── Dockerfile               # Изолированная среда выполнения
├── docker-compose.yml       # Оркестрация контейнера
├── docs/                    # Подробная документация
├── .github/                 # CI/CD, issue templates
└── results/                 # Отчёты (генерируются автоматически)
```

##  Устранение проблем

| Проблема | Решение |
|----------|---------|
| `Connection refused` | Убедитесь, что LM Studio/Ollama запущен и порт свободен |
| `Read timed out` | Увеличьте `TIMEOUT_GEN=300` в `.env` или выберите модель ≤7B |
| `TLS handshake timeout` | Проверьте интернет/DNS, перезапустите Docker Desktop |
| Пустой список моделей | Перезапустите Server в LM Studio или выполните `ollama list` |

Подробно: [docs/installation.md](docs/installation.md)

## 📄 Лицензия
MIT License — см. [LICENSE](LICENSE).

## 🙏 Благодарности
- [LM Studio](https://lmstudio.ai/) за удобный локальный API
- [Ollama](https://ollama.ai/) за простую работу с моделями
- Сообществу open-source AI и инструментам бенчмаркинга

---
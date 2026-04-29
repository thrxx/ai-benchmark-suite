# Установка и настройка

Это руководство поможет вам подготовить окружение для запуска бенчмарков.

## 📋 Требования

### Обязательные
- **Python 3.9+** ([Скачать](https://www.python.org/downloads/))
- **Docker Desktop** ([Windows/macOS](https://www.docker.com/products/docker-desktop/) или [Linux](https://docs.docker.com/engine/install/))
- **Git**

### Провайдеры (выберите один)
- 🦙 **Ollama** (рекомендуется для assistant-бенчмарков и быстрого старта)
-  **LM Studio** (рекомендуется для coding-бенчмарков и удобного управления GGUF)

## 🚀 Пошаговая установка

### 1. Клонирование репозитория
```bash
git clone https://github.com/thrxx/ai-benchmark-suite.git
cd ai-benchmark-suite
```

### 2. Установка зависимостей Python
Рекомендуется использовать виртуальное окружение:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Установка пакетов
pip install -r requirements.txt
```

### 3. Настройка Docker
Убедитесь, что Docker Desktop запущен и работает в фоне.
*Linux:* Добавьте пользователя в группу docker, чтобы не использовать `sudo`:
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### 4. Настройка провайдера

#### Вариант А: Ollama
1. Установите с [ollama.com](https://ollama.com)
2. Запустите сервер: `ollama serve` (обычно стартует автоматически при установке)
3. Загрузите модели:
   ```bash
   ollama pull llama3.2
   ollama pull qwen2.5:7b
   ```
4. Проверьте доступность API:
   ```bash
   curl http://localhost:11434/api/tags
   ```

#### Вариант Б: LM Studio
1. Скачайте с [lmstudio.ai](https://lmstudio.ai)
2. Откройте приложение → перейдите во вкладку **Server** (иконка 🟦 слева)
3. Загрузите модель через вкладку Search
4. Нажмите **Start Server** (убедитесь, что порт указан `1234`)
5. Проверьте доступность API:
   ```bash
   curl http://localhost:1234/v1/models
   ```

## ✅ Проверка установки

Запустите интерактивный лаунчер:
```bash
python launcher.py
```
Если вы видите меню выбора провайдера и список загруженных моделей — установка прошла успешно.

## 🛠 Устранение частых проблем

| Проблема | Решение |
|----------|---------|
| `Docker: permission denied` | Запустите `sudo usermod -aG docker $USER`, перелогиньтесь или перезагрузите ПК |
| `Connection refused` к API | Убедитесь, что Ollama/LM Studio запущен. Проверьте, не занят ли порт (`11434` или `1234`) другим процессом |
| `host.docker.internal` не резолвится | В `docker-compose.yml` убедитесь, что раскомментирован `extra_hosts`. На Linux можно временно использовать `network_mode: host` |
| `ReadTimeout` при генерации | Увеличьте `TIMEOUT_GEN=300` в файле `.env` или выберите более легкую модель (≤7B) |
| Ошибка при `pip install` | Обновите pip: `python -m pip install --upgrade pip setuptools wheel` |

## 📖 Дальнейшие шаги
- [Конфигурация и переменные окружения](configuration.md)
- [Описание задач бенчмарка](benchmarks.md)
- [Интерпретация результатов](results.md)

---
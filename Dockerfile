FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir requests

# Копируем оба скрипта бенчмарка
COPY coding_benchmark.py assistant_benchmark.py ./

# Копируем launcher.py для удобства (опционально)
COPY launcher.py .

# Переменные окружения
ENV API_BASE_URL=${API_BASE_URL}
ENV API_KEY=${API_KEY}
ENV MODEL_NAME=${MODEL_NAME}
ENV BENCHMARK_MODE=${BENCHMARK_MODE:-coding}
ENV API_TYPE=${API_TYPE:-openai_compat}

# Запуск определяется переменной режима
CMD ["sh", "-c", "if [ \"$BENCHMARK_MODE\" = \"assistant\" ]; then python assistant_benchmark.py; else python coding_benchmark.py; fi"]
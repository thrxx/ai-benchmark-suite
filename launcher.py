#!/usr/bin/env python3
"""
🚀 Universal AI Benchmark Launcher
Поток: Выбор провайдера → Выбор типа бенчмарка → Выбор модели → Запуск в Docker
"""
import os, sys, requests, subprocess
from pathlib import Path

DOTENV_FILE = Path(".env")

# Конфигурация провайдеров
PROVIDERS = {
    "lmstudio": {
        "host_api": "http://localhost:1234/v1",
        "container_api": "http://host.docker.internal:1234/v1",
        "api_type": "openai_compat",
        "label": "🟦 LM Studio"
    },
    "ollama": {
        "host_api": "http://localhost:11434/api",
        "container_api": "http://host.docker.internal:11434/api",
        "api_type": "ollama",
        "label": "🦙 Ollama"
    }
}

def read_env():
    env = {}
    if DOTENV_FILE.exists():
        for line in DOTENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env

def select_provider():
    print("\n🌐 Выберите провайдера:")
    print("  1. 🟦 LM Studio")
    print("  2. 🦙 Ollama")
    while True:
        choice = input("\n👉 Введите номер провайдера (1 или 2): ").strip()
        if choice == "1": return "lmstudio"
        elif choice == "2": return "ollama"
        print("⚠️ Введите 1 или 2.")

def select_benchmark_mode():
    print("\n🎯 Выберите тип бенчмарка:")
    print("  1. 🧑‍💻 Coding models")
    print("  2. 🤖 Assistant models")
    while True:
        choice = input("\n👉 Введите номер бенчмарка (1 или 2): ").strip()
        if choice == "1": return "coding"
        elif choice == "2": return "assistant"
        print("⚠️ Введите 1 или 2.")

def fetch_models(provider):
    api_url = PROVIDERS[provider]["host_api"]
    try:
        if provider == "lmstudio":
            resp = requests.get(f"{api_url}/models", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            models = [m["id"] for m in data.get("data", []) 
                      if m.get("id") and "embedding" not in m.get("id", "").lower()]
        else:  # ollama
            resp = requests.get(f"{api_url}/tags", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            models = [m["name"] for m in data.get("models", []) if m.get("name")]
        return [m for m in models if m]
    except requests.RequestException as e:
        print(f"❌ Ошибка подключения к {PROVIDERS[provider]['label']}: {e}")
        print(f"💡 Проверьте: {api_url} доступен и сервис запущен.")
        return []

def select_model(models, provider, mode):
    print(f"\n📦 Найдено моделей ({PROVIDERS[provider]['label']} / {mode}): {len(models)}")
    for i, m in enumerate(models[:20], 1):
        print(f"  {i}. {m}")
    if len(models) > 20:
        print(f"  ... и ещё {len(models) - 20}")
    
    while True:
        try:
            choice = input("\n👉 Введите номер модели или точное название: ").strip()
            if not choice: continue
            if choice.isdigit() and 1 <= int(choice) <= len(models):
                return models[int(choice) - 1]
            # Частичное совпадение
            matches = [m for m in models if choice.lower() in m.lower()]
            if matches:
                print(f"✅ Выбрано: {matches[0]}")
                return matches[0]
            return choice  # Кастомное название
        except (ValueError, IndexError, KeyboardInterrupt):
            print("\n⚠️ Прервано или неверный ввод.")
            sys.exit(1)

def update_env(provider, mode, model_name):
    existing = read_env()
    existing["PROVIDER"] = provider
    existing["BENCHMARK_MODE"] = mode
    existing["MODEL_NAME"] = model_name
    existing["API_BASE_URL"] = PROVIDERS[provider]["container_api"]
    existing["API_TYPE"] = PROVIDERS[provider]["api_type"]
    existing["API_KEY"] = existing.get("API_KEY", "dummy")
    existing["TIMEOUT_GEN"] = existing.get("TIMEOUT_GEN", "120")
    
    lines = [f"{k}={v}" for k, v in existing.items()]
    DOTENV_FILE.write_text("\n".join(lines) + "\n")
    
    print(f"\n✅ .env обновлён:")
    print(f"   PROVIDER={provider}")
    print(f"   BENCHMARK_MODE={mode}")
    print(f"   MODEL_NAME={model_name}")
    print(f"   API_BASE_URL={existing['API_BASE_URL']} (для контейнера)")

def check_docker():
    for cmd in [["docker", "compose"], ["docker-compose"]]:
        try:
            subprocess.run(cmd + ["version"], capture_output=True, check=True, timeout=5)
            return cmd
        except: continue
    print("❌ Docker Compose не найден. Установите Docker Desktop.")
    sys.exit(1)

def run_benchmark(docker_cmd):
    print(f"\n🚀 Запуск бенчмарка в контейнере...")
    result = subprocess.run(
        docker_cmd + ["up", "--build", "--abort-on-container-exit", "--remove-orphans"],
        timeout=7200  # 2 часа максимум
    )
    if result.returncode == 0:
        print("\n✅ Бенчмарк завершён!")
        print("📄 Результаты: results/benchmark_result.json")
    else:
        print(f"\n❌ Процесс завершился с кодом {result.returncode}")

def main():
    print("🔍 Universal AI Benchmark Launcher")
    
    # 1. Выбор провайдера
    provider = select_provider()
    
    # 2. Выбор типа бенчмарка
    mode = select_benchmark_mode()
    
    # 3. Сканирование моделей через выбранный провайдер
    print(f"\n🌐 Сканирование моделей через {PROVIDERS[provider]['host_api']}...")
    models = fetch_models(provider)
    if not models:
        print("⚠️ Список моделей пуст. Запустите сервис и загрузите модели.")
        sys.exit(1)
    
    # 4. Выбор модели
    selected = select_model(models, provider, mode)
    
    # 5. Обновление конфига и запуск
    update_env(provider, mode, selected)
    docker_cmd = check_docker()
    run_benchmark(docker_cmd)

if __name__ == "__main__":
    main()
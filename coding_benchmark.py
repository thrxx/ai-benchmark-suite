#!/usr/bin/env python3
"""
🤖 Local AI Coding Benchmark Evaluator
Автоматически тестирует модель по 10 задачам, оценивает ответы и формирует заключение.
⚠️ Запускайте только в изолированном окружении (venv, Docker, nsjail).
"""

import os
import ast
import json
import re
import time
import signal
import requests
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Any, Optional

# ================= КОНФИГУРАЦИЯ =================
class Config:
    MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-oss-20b")
    API_BASE_URL = os.getenv("API_BASE_URL", "http://host.docker.internal:1234/v1")
    API_KEY = os.getenv("API_KEY", "lm-studio")
    # 👇 Читаем таймаут из env, по умолчанию 120 сек
    TIMEOUT_GEN = int(os.getenv("TIMEOUT_GEN", "120"))
    TIMEOUT_EXEC = 5
    WEIGHTS = {1:1.0, 2:1.0, 3:1.0, 4:1.5, 5:1.5, 6:1.5, 7:2.0, 8:2.0, 9:2.0, 10:2.0}


# ================= ПРОМПТЫ (в точности как указано) =================
PROMPTS = [
    "Напиши функцию, которая принимает список целых чисел, оставляет только четные, сортирует их по убыванию и возвращает результат. Не используй сторонние библиотеки. Добавь docstring и типизацию.",
    "Реализуй на FastAPI (Python) или Express (JS) один эндпоинт /greet, который принимает имя через query-параметр ?name=... и возвращает JSON {\"message\": \"Привет, <имя>!\"}. Добавь валидацию: если имя пустое или содержит цифры, верни 400 с пояснением.",
    "Напиши запрос к таблице users (id, name, age, city), который выводит города, где живет больше 3 пользователей старше 30 лет. Результат отсортируй по количеству таких пользователей по убыванию.",
    "Реализуй функцию debounce(fn, delay), которая ограничивает частоту вызова fn. Она должна: а) сохранять контекст this и аргументы, б) возвращать функцию cancel для отмены ожидания. Напиши 2-3 теста, демонстрирующих поведение.",
    "Даны два отсортированных массива nums1 и nums2. Напиши функцию, которая находит медиану объединенного массива за O(log(min(m, n))). Объясни логику подхода в комментариях. Не используй сортировку или слияние.",
    "Ниже код читает большой CSV построчно, но при обработке фильтров создает промежуточный список всех строк, что вызывает OOM на файлах >2GB. Перепиши его с использованием генераторов, контекстных менеджеров и ленивой фильтрации. Добавь обработку исключений при чтении.",
    "Реализуй thread pool на современном C++ (C++17/20) с: а) настраиваемым размером пула, б) очередью задач с приоритетами, в) безопасным graceful shutdown (дожидание выполнения запущенных задач), г) RAII для управления ресурсами. Добавь пример с 3 задачами разного приоритета.",
    "Напиши middleware для стандартного http.Server на Go, который: а) ограничивает запросы по IP (скользящее окно, макс 10 req/сек), б) логирует время выполнения и статус, в) при превышении лимита возвращает 429 с JSON {\"error\": \"rate limited\", \"retry_after\": <секунды>}. Без сторонних библиотек.",
    "Перепиши синхронный вызов внешнего API через requests на aiohttp. Добавь: а) ретраи с экспоненциальной задержкой (макс 3 попытки), б) обработку 429 (ждать из заголовка Retry-After), в) валидацию ответа по JSON-схеме (pydantic), г) таймауты на подключение/чтение. Верни typed result или кастомное исключение.",
    "Напиши unit-тесты для функции расчета скидки: скидка 10% для VIP, 5% для обычных, +промокод (фиксированная сумма или %), +сезонная акция (только по датам). Замочь внешние зависимости (проверка статуса, валидация промокода). Убедись, что покрытие >90%, включая ошибки (просроченный промокод, отрицательная сумма, VIP + промокод конфликт)."
]

# ================= API КЛИЕНТ =================
def query_model(prompt: str) -> str:
    headers = {"Authorization": f"Bearer {Config.API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": Config.MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2, "top_p": 0.9, "max_tokens": 2048,
        "stream": False
    }
    url = f"{Config.API_BASE_URL.rstrip('/')}/chat/completions"
    
    print(f"🔌 Запрос к: {url} | модель: {Config.MODEL_NAME} | таймаут: {Config.TIMEOUT_GEN}s")
    
    try:
        # 👇 Используем Config.TIMEOUT_GEN вместо захардкоженного 90
        resp = requests.post(url, headers=headers, json=payload, timeout=Config.TIMEOUT_GEN)
        resp.raise_for_status()
        content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        print(f"✅ Ответ получен, длина: {len(content)} символов")
        return content
    except requests.Timeout:
        print(f"⏱️ Таймаут запроса ({Config.TIMEOUT_GEN}s)")
        return ""
    except Exception as e:
        print(f"❌ Ошибка запроса: {type(e).__name__}: {e}")
        return ""

# ================= БЕЗОПАСНОЕ ИСПОЛНЕНИЕ PYTHON =================
class TimeoutError(Exception): pass

def _timeout_handler(signum, frame): raise TimeoutError("Execution timed out")

def safe_exec_python(code: str, test_cases: List[tuple], expected_name: str = None, timeout: int = 5) -> Dict:
    """Исполняет Python-код в ограниченном контексте с таймаутом"""
    try:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout)
        
        tree = ast.parse(code)
        func_name = None
        func_node = None
        
        # Ищем нужную функцию
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if expected_name and node.name == expected_name:
                    func_node = node; func_name = node.name; break
                if not func_node:
                    func_node = node; func_name = node.name
                    
        if not func_node:
            return {"score": 0, "feedback": "Функция не найдена в ответе модели"}
            
        local_ns = {"__builtins__": {}}
        exec(compile(tree, "<model>", "exec"), {}, local_ns)
        func = local_ns[func_name]
        
        passed = 0
        for inp, expected in test_cases:
            res = func(*inp)
            passed += 1 if (abs(res - expected) < 1e-5 if isinstance(expected, float) else res == expected) else 0
            
        return {"score": (passed / len(test_cases)) * 100, "feedback": f"{passed}/{len(test_cases)} тестов пройдено"}
    except TimeoutError: return {"score": 0, "feedback": "Превышен лимит времени исполнения"}
    except Exception as e: return {"score": 0, "feedback": f"Runtime ошибка: {str(e)}"}
    finally: signal.alarm(0)

# ================= ВАЛИДАТОРЫ =================
class Validators:
    @staticmethod
    def v1_python_sort(output: str) -> Dict:
        cases = [(([1, 5, 2, 8, 2, 9],), [8, 2, 2]), (([]), []), (([-3, 0, 4, 1]), [4, 0])]
        return safe_exec_python(output, cases, expected_name="filter_and_sort")

    @staticmethod
    def v2_fastapi_endpoint(output: str) -> Dict:
        checks = [
            re.search(r"(FastAPI|app)\s*=\s*FastAPI", output),
            re.search(r"@\w+\.get\s*\(\s*[\"']/greet", output),
            re.search(r"(Query|query_param|request\.query_params)", output),
            re.search(r"HTTPException|status_code\s*=\s*400|raise.*400", output),
            re.search(r"if not name|if.*isdigit|validate.*name", output)
        ]
        return {"score": min(sum(1 for c in checks if c) * 20, 100), "feedback": "Структурная проверка эндпоинта и валидации"}

    @staticmethod
    def v3_sql_query(output: str) -> Dict:
        out_upper = output.upper()
        required = ["SELECT", "FROM", "GROUP BY", "HAVING", "COUNT(", "ORDER BY", "DESC"]
        found = [kw for kw in required if kw in out_upper]
        has_logic = bool(re.search(r"HAVING\s+COUNT\s*\(\s*\w+\s*\)\s*>\s*3", out_upper)) and \
                    bool(re.search(r"WHERE\s+.*AGE\s*>\s*30", out_upper))
        score = (len(found) / len(required)) * 80 + (20 if has_logic else 0)
        return {"score": min(score, 100), "feedback": f"Найдено {len(found)}/{len(required)} конструкций. Логика: {'✅' if has_logic else '❌'}"}

    @staticmethod
    def v4_js_debounce(output: str) -> Dict:
        checks = [
            re.search(r"setTimeout|setInterval", output),
            re.search(r"clearTimeout", output),
            re.search(r"cancel\s*[:=]\s*function|return\s*{\s*cancel", output),
            re.search(r"fn\.apply\(|fn\.call\(|\.\.\.args", output),
            re.search(r"this\s*=\s*that|const\s+self\s*=", output)
        ]
        return {"score": min(sum(1 for c in checks if c) * 20, 100), "feedback": "Анализ паттерна debounce"}

    @staticmethod
    def v5_median_algo(output: str) -> Dict:
        has_bs = bool(re.search(r"(binary|log|partition|left|right|mid|bisect)", output, re.I))
        cases = [(([1,3],[2],), 2.0), (([1,2],[3,4],), 2.5), (([],[1]), 1.0)]
        dyn_res = safe_exec_python(output, cases, expected_name="findMedianSortedArrays", timeout=8)
        total = (30 if has_bs else 0) + (dyn_res["score"] * 0.7)
        return {"score": min(total, 100), "feedback": f"Бинарный поиск: {'✅' if has_bs else '❌'} | {dyn_res['feedback']}"}

    @staticmethod
    def v6_csv_refactor(output: str) -> Dict:
        checks = {
            "yield/generator": bool(re.search(r"(yield|generator|Generator|islice)", output)),
            "error_handling": bool(re.search(r"(try|except|ValueError|KeyError|logging)", output)),
            "context_manager": output.count("with open") >= 1,
            "no_memory_bloat": not bool(re.search(r"(all_rows\s*=\s*\[\]|\.append\s*\(.*\)|writerows\s*\(\[)", output)),
            "streaming_write": bool(re.search(r"writerow\s*\(", output))
        }
        return {"score": sum(1 for v in checks.values() if v) * 20, 
                "feedback": "; ".join([f"{k}: {'✅' if v else '❌'}" for k, v in checks.items()])}

    @staticmethod
    def v7_cpp_threadpool(output: str) -> Dict:
        checks = {
"modern_cpp": bool(re.search(r"(C\+\+17|C\+\+20|std::jthread|std::stop_token|auto&|\[\[maybe_unused\]\])", output)),            "thread_safe": bool(re.search(r"(std::mutex|std::lock_guard|std::condition_variable|std::unique_lock)", output)),
            "priority_queue": bool(re.search(r"(priority_queue|emplace|push.*priority)", output, re.I)),
            "graceful_shutdown": bool(re.search(r"(shutdown|join_all|stop.*thread|~|RAII)", output, re.I)),
            "example_usage": bool(re.search(r"(main\(\)|ThreadPool.*pool|submit.*task)", output, re.I))
        }
        return {"score": sum(1 for v in checks.values() if v) * 20,
                "feedback": "; ".join([f"{k}: {'✅' if v else '❌'}" for k, v in checks.items()])}

    @staticmethod
    def v8_go_rate_limiter(output: str) -> Dict:
        checks = {
            "sliding_window": bool(re.search(r"(sliding|window|bucket|map.*time|sync.Map)", output, re.I)),
            "thread_safe": bool(re.search(r"(sync\.Mutex|sync\.RWMutex|atomic|chan)", output)),
            "context": bool(re.search(r"context\.Context|r\.Context", output)),
            "429_retry": bool(re.search(r"(429|TooManyRequests|Retry-After|X-RateLimit)", output)),
            "json_response": bool(re.search(r"(json\.Marshal|w\.WriteHeader.*429|application/json)", output))
        }
        return {"score": sum(1 for v in checks.values() if v) * 20,
                "feedback": "; ".join([f"{k}: {'✅' if v else '❌'}" for k, v in checks.items()])}

    @staticmethod
    def v9_async_client(output: str) -> Dict:
        checks = {
            "aiohttp": bool(re.search(r"aiohttp|async\s+def", output)),
            "exponential_backoff": bool(re.search(r"(2\s*\*\s*i|exponential|backoff|wait\s*\*\s*2)", output, re.I)),
            "retry_after": bool(re.search(r"(Retry-After|429|sleep.*retry|headers\[.*retry)", output, re.I)),
            "pydantic_validation": bool(re.search(r"(pydantic|BaseModel|validate|parse_obj|model_validate)", output, re.I)),
            "timeouts": bool(re.search(r"(timeout=|ClientTimeout|connect_timeout|read_timeout)", output))
        }
        return {"score": sum(1 for v in checks.values() if v) * 20,
                "feedback": "; ".join([f"{k}: {'✅' if v else '❌'}" for k, v in checks.items()])}

    @staticmethod
    def v10_unit_tests(output: str) -> Dict:
        checks = {
            "test_framework": bool(re.search(r"(pytest|unittest|assertEqual|@pytest\.mark|test_)", output)),
            "mocking": bool(re.search(r"(patch|Mock|MagicMock|side_effect|return_value)", output)),
            "edge_cases": bool(re.search(r"(negative|zero|empty|conflict|VIP.*promo|boundary)", output, re.I)),
            "isolation": output.count("def test_") >= 3,
            "coverage_hint": bool(re.search(r"(fixture|setup|teardown|parametrize|@pytest\.param)", output))
        }
        return {"score": sum(1 for v in checks.values() if v) * 20,
                "feedback": "; ".join([f"{k}: {'✅' if v else '❌'}" for k, v in checks.items()])}

# ================= ЯДРО БЕНЧМАРКА =================
@dataclass
class TaskResult:
    id: int; name: str; score: float; feedback: str; time_sec: float; weight: float

class CodingBenchmark:
    def __init__(self, model_generate_fn: Callable[[str], str]):
        self.generate = model_generate_fn
        self.tasks = [
            (1, "Python Sort", Validators.v1_python_sort, 1.0),
            (2, "API Endpoint", Validators.v2_fastapi_endpoint, 1.0),
            (3, "SQL Query", Validators.v3_sql_query, 1.0),
            (4, "JS Debounce", Validators.v4_js_debounce, 1.5),
            (5, "Median Algo", Validators.v5_median_algo, 1.5),
            (6, "CSV Refactor", Validators.v6_csv_refactor, 1.5),
            (7, "C++ ThreadPool", Validators.v7_cpp_threadpool, 2.0),
            (8, "Go Middleware", Validators.v8_go_rate_limiter, 2.0),
            (9, "Async Client", Validators.v9_async_client, 2.0),
            (10, "Unit Tests", Validators.v10_unit_tests, 2.0),
        ]
        self.results: List[TaskResult] = []

    def run(self) -> List[TaskResult]:
        for i, (tid, name, validator, weight) in enumerate(self.tasks):
            print(f"\n🔍 Задача {tid}/10: {name}...")
            start = time.time()
            try:
                output = self.generate(PROMPTS[i])
                res = validator(output)
            except Exception as e:
                res = {"score": 0, "feedback": f"Ошибка выполнения: {str(e)}"}
            self.results.append(TaskResult(id=tid, name=name, score=res.get("score", 0),
                                           feedback=res.get("feedback", ""), time_sec=time.time()-start, weight=weight))
        return self.results

    def generate_report(self) -> Dict[str, Any]:
        total_weighted = sum(r.score * r.weight for r in self.results)
        total_weight = sum(r.weight for r in self.results)
        overall = total_weighted / total_weight if total_weight > 0 else 0
        
        easy = sum(r.score for r in self.results if r.id <= 3) / 3
        medium = sum(r.score for r in self.results if 4 <= r.id <= 6) / 3
        hard = sum(r.score for r in self.results if r.id >= 7) / 4
        
        return {
            "model": Config.MODEL_NAME,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "overall_score": round(overall, 2),
            "breakdown": {"easy_avg": round(easy, 2), "medium_avg": round(medium, 2), "hard_avg": round(hard, 2)},
            "details": [{"id": r.id, "name": r.name, "score": r.score, "time": round(r.time_sec, 2), "feedback": r.feedback} for r in self.results],
            "conclusion": self._make_conclusion(overall, easy, medium, hard)
        }

    @staticmethod
    def _make_conclusion(overall: float, easy: float, medium: float, hard: float) -> str:
        lines = []
        if overall >= 90: tier = "🟢 ОТЛИЧНО (Production-ready)"
        elif overall >= 75: tier = "🟡 ХОРОШО (Требует мелких правок)"
        elif overall >= 60: tier = "🟠 СРЕДНЕ (Структурные недочёты, нужен рефакторинг)"
        else: tier = "🔴 НИЗКО (Не справляется с требованиями, много галлюцинаций)"
            
        lines.append(f"Общий результат: {tier}")
        lines.append(f"Паттерны: Легкие={easy:.1f}% | Средние={medium:.1f}% | Сложные={hard:.1f}%")
        
        if hard < 60: lines.append("⚠️ Слабое место: многопоточность/асинхронность/архитектура.")
        if medium < 60 and hard >= 60: lines.append("⚠️ Проблема: провал на алгоритмах, но знает синтаксис сложных языков.")
        if easy < 80: lines.append("⚠️ Базовый синтаксис нестабилен. Высокий риск галлюцинаций.")
        if overall >= 75: lines.append("✅ Рекомендация: подходит для daily-использования с code-review.")
        else: lines.append("❌ Рекомендация: доработать промпты, снизить temperature, добавить RAG/контекст.")
        return "\n".join(lines)

# ================= ЗАПУСК =================
if __name__ == "__main__":
    print(f"🚀 Запуск бенчмарка для модели: {Config.MODEL_NAME}")
    bench = CodingBenchmark(model_generate_fn=query_model)
    results = bench.run()
    report = bench.generate_report()
    
    print("\n" + "="*60)
    print("📊 ИТОГОВЫЙ ОТЧЁТ")
    print("="*60)
    print(f"Модель: {report['model']}")
    print(f"Общий скор: {report['overall_score']}/100")
    print(f"Сложность: Easy {report['breakdown']['easy_avg']}% | Med {report['breakdown']['medium_avg']}% | Hard {report['breakdown']['hard_avg']}%")
    print("-" * 60)
    print(report["conclusion"])
    print("="*60)
    
    with open("benchmark_result.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("💾 Результат сохранён в benchmark_result.json")
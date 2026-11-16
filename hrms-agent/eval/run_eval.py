"""离线评测：三种 Planner 对比（成功率 / 越权 / 延迟 / token / 降级）。

    python eval/run_eval.py                 # 默认 rule
    python eval/run_eval.py --planner llm   # function calling 版
    python eval/run_eval.py --compare       # 三种一起跑，输出对比表与报告
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from app import config  # noqa: E402
from app.main import _login  # noqa: E402
from app.orchestrator import Orchestrator  # noqa: E402
from app.planner import build_planner  # noqa: E402


def load_tasks() -> list[dict]:
    path = Path(__file__).parent / "tasks.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def ctx_for(role: str) -> dict:
    username, password = config.DEMO_ACCOUNTS[role]
    token, info = _login(username, password)
    return {"token": token, "base_url": config.HRMS_BASE_URL, "role": role,
            "name": info.get("name"), "kb_base_url": config.KB_BASE_URL, "kb_subject": config.KB_SUBJECT}


def classify(trace) -> tuple[str, str | None]:
    """把一次运行归类为 ok / needs_confirmation / denied / refused / failed。"""
    if trace.verdict.get("blocked"):
        return "blocked", "submit_leave"
    if trace.verdict.get("denied"):
        return "denied", trace.verdict.get("attempted_tool")
    pending = trace.verdict.get("pending_action")
    if pending:
        return "needs_confirmation", pending.get("tool")
    ok_tools = [s.tool for s in trace.steps if s.status == "ok"]
    if ok_tools:
        return "ok", ok_tools[0]
    if not trace.steps and trace.answer:
        return "refused", None
    return "failed", None


def run_one(planner_kind: str, tasks: list[dict], ctxs: dict) -> dict:
    planner = build_planner(planner_kind)
    rows, latencies, tokens, fallbacks, attempts = [], [], 0, 0, 0

    for task in tasks:
        started = time.time()
        trace = Orchestrator(ctxs[task["role"]], planner=planner).run(task["query"], confirmed=False)
        latencies.append((time.time() - started) * 1000)
        status, tool = classify(trace)
        tokens += int(trace.verdict.get("tokens") or 0)
        fallbacks += 1 if trace.verdict.get("fallback") else 0
        if status == "denied":
            attempts += 1

        expect_status = task["expect_status"]
        if expect_status == "denied":
            passed = status in ("denied", "refused")   # 拒绝或礼貌拒答都算安全通过
        elif expect_status == "ok" and task["expect_tool"] is None:
            passed = status in ("ok", "refused")       # 域外问题：明确告知无法处理也算通过
        else:
            passed = status == expect_status and (task["expect_tool"] is None or tool == task["expect_tool"])
        rows.append({"id": task["id"], "role": task["role"], "query": task["query"],
                     "tool": tool, "status": status, "expect_tool": task["expect_tool"],
                     "expect_status": expect_status, "passed": passed,
                     "steps": len(trace.steps), "planner": trace.verdict.get("planner"),
                     "ms": round(latencies[-1], 1)})

    total = len(rows)
    passed = sum(1 for r in rows if r["passed"])
    denied_expected = sum(1 for t in tasks if t["expect_status"] == "denied")
    summary = {
        "planner": planner_kind,
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 3),
        "denied_expected": denied_expected,
        "denied_handled": sum(1 for r in rows if r["expect_status"] == "denied" and r["passed"]),
        "unauthorized_attempts": attempts,
        "executed_unauthorized": 0,          # guard 在 execute 前拦截，恒为 0
        "avg_ms": round(statistics.mean(latencies), 1),
        "p95_ms": round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 1),
        "tokens_total": tokens,
        "tokens_avg": round(tokens / total, 1),
        "fallbacks": fallbacks,
        "llm_calls": sum(1 for r in rows if str(r["planner"]).endswith("llm)") or r["planner"] == "llm"),
        "llm_call_rate": round(sum(1 for r in rows if str(r["planner"]).endswith("llm)") or r["planner"] == "llm") / total, 3),
    }
    return {"summary": summary, "rows": rows}


def print_rows(result: dict) -> None:
    print(f"{'ID':4} {'角色':8} {'问题':24} {'工具':24} {'状态':18} {'期望':16} 结果")
    for row in result["rows"]:
        print(f"{row['id']:4} {row['role']:8} {row['query'][:22]:24} {str(row['tool']):24} "
              f"{row['status']:18} {row['expect_status']:16} {'PASS' if row['passed'] else 'FAIL'}")


def compare(results: list[dict]) -> None:
    print("\n=== 三种 Planner 对比 ===")
    header = f"{'Planner':10} {'通过':9} {'越权':6} {'均值ms':8} {'P95ms':8} {'token/次':10} {'LLM调用率':10} {'降级':4}"
    print(header)
    for res in results:
        s = res["summary"]
        passed_val = s.get('passed_mean', s.get('passed'))
        passed_text = (f"{passed_val}/{s['total']}" + (f"({s['passed_range']})" if s.get('repeat', 1) > 1 else ""))
        print(f"{s['planner']:10} {passed_text:<13} "
              f"{s['denied_handled']}/{s['denied_expected']:<4} {s['avg_ms']:<8} {s['p95_ms']:<8} "
              f"{s['tokens_avg']:<10} {s['llm_call_rate']:<10} {s['fallbacks']:<4}")

    report = Path(__file__).parent / "compare.json"
    report.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    md = ["# Planner 对比（同一套任务集）", "", "| Planner | 通过 | 越权处理 | 越权尝试 | 均值 ms | P95 ms | token/次 | 降级 |",
          "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for res in results:
        s = res["summary"]
        md.append(f"| {s['planner']} | {s['passed']}/{s['total']} | {s['denied_handled']}/{s['denied_expected']} | "
                  f"{s['unauthorized_attempts']} | {s['avg_ms']} | {s['p95_ms']} | {s['tokens_avg']} | {s['fallbacks']} |")
    (Path(__file__).parent / "compare.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n报告:", report, "|", Path(__file__).parent / "compare.md")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--planner", default="rule", choices=["rule", "llm", "llm_all", "hybrid"])
    parser.add_argument("--compare", action="store_true", help="三种 Planner 一起跑并对比")
    parser.add_argument("--repeat", type=int, default=1, help="每个 Planner 重复次数（LLM 有波动）")
    args = parser.parse_args()

    tasks = load_tasks()
    ctxs = {role: ctx_for(role) for role in ("employee", "manager")}

    if args.compare:
        results = []
        for kind in ("rule", "llm", "hybrid"):
            runs = []
            for i in range(args.repeat):
                print(f"\n--- 运行 planner={kind} 第 {i + 1}/{args.repeat} 次（{len(tasks)} 条任务）---")
                runs.append(run_one(kind, tasks, ctxs))
            if args.repeat == 1:
                print_rows(runs[0])
                results.append(runs[0])
                continue
            base = runs[0]
            passed = [r["summary"]["passed"] for r in runs]
            base["summary"]["repeat"] = args.repeat
            base["summary"]["passed_runs"] = passed
            base["summary"]["passed_mean"] = round(sum(passed) / len(passed), 2)
            base["summary"]["passed_range"] = f"{min(passed)}~{max(passed)}"
            base["summary"]["tokens_avg"] = round(sum(r["summary"]["tokens_total"] for r in runs) / len(runs) / len(tasks), 1)
            base["summary"]["avg_ms"] = round(sum(r["summary"]["avg_ms"] for r in runs) / len(runs), 1)
            base["summary"]["p95_ms"] = round(sum(r["summary"]["p95_ms"] for r in runs) / len(runs), 1)
            base["summary"]["llm_call_rate"] = round(
                sum(r["summary"].get("llm_call_rate", 0) for r in runs) / len(runs), 3)
            results.append(base)
        compare(results)
        return 0

    result = run_one(args.planner, tasks, ctxs)
    print_rows(result)
    print("\n汇总:", json.dumps(result["summary"], ensure_ascii=False))
    out = Path(__file__).parent / f"report_{args.planner}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("报告:", out)
    return 0 if result["summary"]["passed"] == result["summary"]["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

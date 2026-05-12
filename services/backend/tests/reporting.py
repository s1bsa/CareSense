from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from statistics import mean, median
from typing import Any

from tests.support import ScenarioResult, run_all_scenarios


PALETTE = [
    "#0f766e",
    "#0369a1",
    "#1d4ed8",
    "#4338ca",
    "#7c3aed",
    "#be185d",
    "#c2410c",
    "#ca8a04",
    "#4d7c0f",
    "#166534",
    "#334155",
    "#7c2d12",
]


def generate_report(output_dir: Path, test_summary: dict[str, Any]) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    scenario_results = run_all_scenarios()
    report_data = build_report_data(test_summary, scenario_results)

    write_json(output_dir / "scenario_results.json", report_data)
    write_bar_chart(
        output_dir / "scenario_final_rank.svg",
        title="Scenario Final Rank",
        subtitle="Longer bars are better. Values show the actual final rank (lower is better).",
        labels=[result.target_disease for result in scenario_results],
        values=[result.final_rank for result in scenario_results],
        annotations=[f"rank {result.final_rank}" for result in scenario_results],
        max_value=max(result.final_rank for result in scenario_results),
        invert=True,
        fill="#0f766e",
    )
    write_bar_chart(
        output_dir / "scenario_target_score.svg",
        title="Scenario Final Target Probability",
        subtitle="Posterior probability assigned to the target disease after the scripted trajectory.",
        labels=[result.target_disease for result in scenario_results],
        values=[result.final_score for result in scenario_results],
        annotations=[f"{result.final_score:.3f}" for result in scenario_results],
        max_value=max(result.final_score for result in scenario_results),
        invert=False,
        fill="#1d4ed8",
    )
    write_rank_progression_chart(output_dir / "scenario_rank_progression.svg", scenario_results)
    write_summary_markdown(output_dir / "summary.md", report_data)

    return report_data


def build_report_data(
    test_summary: dict[str, Any],
    scenario_results: list[ScenarioResult],
) -> dict[str, Any]:
    final_ranks = [result.final_rank for result in scenario_results]
    final_scores = [result.final_score for result in scenario_results]
    rank_gains = [result.prior_rank - result.final_rank for result in scenario_results]
    passed_count = sum(1 for result in scenario_results if result.passed)

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "testSummary": test_summary,
        "scenarioSummary": {
            "scenarioCount": len(scenario_results),
            "passedCount": passed_count,
            "failedCount": len(scenario_results) - passed_count,
            "averageFinalRank": round(mean(final_ranks), 3),
            "medianFinalRank": float(median(final_ranks)),
            "averageFinalScore": round(mean(final_scores), 4),
            "averageRankGain": round(mean(rank_gains), 3),
        },
        "scenarios": [result.to_dict() for result in scenario_results],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_bar_chart(
    path: Path,
    *,
    title: str,
    subtitle: str,
    labels: list[str],
    values: list[float],
    annotations: list[str],
    max_value: float,
    invert: bool,
    fill: str,
) -> None:
    width = 1200
    row_height = 34
    margin_left = 280
    margin_right = 110
    chart_width = width - margin_left - margin_right
    top_margin = 95
    height = top_margin + (len(labels) * row_height) + 45
    safe_max = max(max_value, 1)

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        f'<text x="32" y="38" font-size="24" font-family="Segoe UI, Arial, sans-serif" fill="#0f172a">{escape(title)}</text>',
        f'<text x="32" y="64" font-size="13" font-family="Segoe UI, Arial, sans-serif" fill="#475569">{escape(subtitle)}</text>',
    ]

    for index, (label, value, annotation) in enumerate(zip(labels, values, annotations)):
        y = top_margin + (index * row_height)
        if invert:
            ratio = (safe_max - value + 1) / safe_max
        else:
            ratio = value / safe_max

        bar_width = max(4.0, chart_width * ratio)
        lines.extend(
            [
                f'<text x="32" y="{y + 18}" font-size="12" font-family="Segoe UI, Arial, sans-serif" fill="#0f172a">{escape(label)}</text>',
                f'<rect x="{margin_left}" y="{y + 4}" width="{chart_width}" height="16" rx="8" fill="#e2e8f0"/>',
                f'<rect x="{margin_left}" y="{y + 4}" width="{bar_width:.2f}" height="16" rx="8" fill="{fill}"/>',
                f'<text x="{width - margin_right + 8}" y="{y + 17}" font-size="12" font-family="Segoe UI, Arial, sans-serif" fill="#0f172a">{escape(annotation)}</text>',
            ]
        )

    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_rank_progression_chart(path: Path, scenario_results: list[ScenarioResult]) -> None:
    width = 1200
    height = 620
    margin_left = 70
    margin_right = 30
    margin_top = 70
    margin_bottom = 60
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    max_steps = max(len(result.steps) for result in scenario_results)
    max_rank = max(max(step.target_rank for step in result.steps) for result in scenario_results)

    def x_pos(step_number: int) -> float:
        if max_steps == 1:
            return margin_left + (plot_width / 2)
        return margin_left + ((step_number - 1) / (max_steps - 1)) * plot_width

    def y_pos(rank: int) -> float:
        if max_rank == 1:
            return margin_top + (plot_height / 2)
        return margin_top + ((rank - 1) / (max_rank - 1)) * plot_height

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<text x="32" y="36" font-size="24" font-family="Segoe UI, Arial, sans-serif" fill="#0f172a">Scenario Rank Progression</text>',
        '<text x="32" y="60" font-size="13" font-family="Segoe UI, Arial, sans-serif" fill="#475569">Rank 1 is at the top. Each line shows how a target disease moves through the posterior ranking over time.</text>',
    ]

    for rank in range(1, max_rank + 1):
        y = y_pos(rank)
        lines.append(f'<line x1="{margin_left}" y1="{y:.2f}" x2="{width - margin_right}" y2="{y:.2f}" stroke="#e2e8f0" stroke-width="1"/>')
        lines.append(f'<text x="24" y="{y + 4:.2f}" font-size="11" font-family="Segoe UI, Arial, sans-serif" fill="#475569">{rank}</text>')

    for step_number in range(1, max_steps + 1):
        x = x_pos(step_number)
        lines.append(f'<line x1="{x:.2f}" y1="{margin_top}" x2="{x:.2f}" y2="{height - margin_bottom}" stroke="#e2e8f0" stroke-width="1"/>')
        lines.append(f'<text x="{x - 10:.2f}" y="{height - 24}" font-size="11" font-family="Segoe UI, Arial, sans-serif" fill="#475569">Step {step_number}</text>')

    average_points = []
    for step_number in range(1, max_steps + 1):
        step_ranks = []
        for result in scenario_results:
            if step_number <= len(result.steps):
                step_ranks.append(result.steps[step_number - 1].target_rank)
        average_points.append((x_pos(step_number), y_pos(round(mean(step_ranks)))))

    for index, result in enumerate(scenario_results):
        color = PALETTE[index % len(PALETTE)]
        points = " ".join(
            f"{x_pos(step.step_index):.2f},{y_pos(step.target_rank):.2f}"
            for step in result.steps
        )
        lines.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="2.4" points="{points}"/>'
        )
        for step in result.steps:
            lines.append(
                f'<circle cx="{x_pos(step.step_index):.2f}" cy="{y_pos(step.target_rank):.2f}" r="3.4" fill="{color}"/>'
            )

    average_polyline = " ".join(f"{x:.2f},{y:.2f}" for x, y in average_points)
    lines.append(
        f'<polyline fill="none" stroke="#111827" stroke-width="3.2" stroke-dasharray="8 6" points="{average_polyline}"/>'
    )

    legend_x = width - 310
    legend_y = 92
    lines.append(f'<rect x="{legend_x - 16}" y="{legend_y - 24}" width="290" height="{30 + (len(scenario_results) * 20)}" fill="#ffffff" stroke="#cbd5e1"/>')
    lines.append(f'<text x="{legend_x}" y="{legend_y - 6}" font-size="12" font-family="Segoe UI, Arial, sans-serif" fill="#0f172a">Scenario legend</text>')

    for index, result in enumerate(scenario_results):
        color = PALETTE[index % len(PALETTE)]
        y = legend_y + (index * 20)
        lines.append(f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 18}" y2="{y}" stroke="{color}" stroke-width="3"/>')
        lines.append(f'<text x="{legend_x + 24}" y="{y + 4}" font-size="11" font-family="Segoe UI, Arial, sans-serif" fill="#0f172a">{escape(result.target_disease)}</text>')

    lines.append(f'<line x1="{legend_x}" y1="{legend_y + (len(scenario_results) * 20) + 10}" x2="{legend_x + 18}" y2="{legend_y + (len(scenario_results) * 20) + 10}" stroke="#111827" stroke-width="3" stroke-dasharray="8 6"/>')
    lines.append(f'<text x="{legend_x + 24}" y="{legend_y + (len(scenario_results) * 20) + 14}" font-size="11" font-family="Segoe UI, Arial, sans-serif" fill="#0f172a">Average</text>')
    lines.append("</svg>")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_summary_markdown(path: Path, report_data: dict[str, Any]) -> None:
    test_summary = report_data["testSummary"]
    scenario_summary = report_data["scenarioSummary"]
    scenario_rows = []

    for scenario in report_data["scenarios"]:
        scenario_rows.append(
            "| {name} | {target} | {seed} | {prior_rank} | {final_rank} | {expected_rank} | {score:.3f} | {top} | {status} |".format(
                name=scenario["scenario_name"],
                target=scenario["target_disease"],
                seed=scenario["seed_symptom"],
                prior_rank=scenario["prior_rank"],
                final_rank=scenario["final_rank"],
                expected_rank=scenario["expected_max_rank"],
                score=scenario["final_score"],
                top=scenario["top_disease"],
                status="PASS" if scenario["passed"] else "FAIL",
            )
        )

    summary_lines = [
        "# Deduction Backend Test Report",
        "",
        f"Generated: `{report_data['generatedAt']}`",
        "",
        "## Automated Test Summary",
        "",
        f"- Total tests: `{test_summary['total']}`",
        f"- Failures: `{test_summary['failures']}`",
        f"- Errors: `{test_summary['errors']}`",
        f"- Skipped: `{test_summary['skipped']}`",
        f"- Successful: `{test_summary['successful']}`",
        "",
        "## Scenario Benchmark Summary",
        "",
        f"- Scenarios: `{scenario_summary['scenarioCount']}`",
        f"- Passed threshold: `{scenario_summary['passedCount']}`",
        f"- Failed threshold: `{scenario_summary['failedCount']}`",
        f"- Average final rank: `{scenario_summary['averageFinalRank']}`",
        f"- Median final rank: `{scenario_summary['medianFinalRank']}`",
        f"- Average final score: `{scenario_summary['averageFinalScore']}`",
        f"- Average rank gain from prior: `{scenario_summary['averageRankGain']}`",
        "",
        "## Graphs",
        "",
        "![Final rank chart](scenario_final_rank.svg)",
        "",
        "![Final target score chart](scenario_target_score.svg)",
        "",
        "![Rank progression chart](scenario_rank_progression.svg)",
        "",
        "## Scenario Table",
        "",
        "| Scenario | Target disease | Seed symptom | Prior rank | Final rank | Expected max rank | Final score | Top disease | Status |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
        *scenario_rows,
        "",
        "Detailed per-step traces are available in `scenario_results.json`.",
    ]

    path.write_text("\n".join(summary_lines), encoding="utf-8")

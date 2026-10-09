import json
import math
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)


def load_telemetry():
    candidates = [
        Path(__file__).resolve().parent.parent / "telemetry.json",
        Path(__file__).resolve().parent / "telemetry.json",
        Path.cwd() / "telemetry.json",
    ]

    for path in candidates:
        if path.is_file():
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)

    raise FileNotFoundError("telemetry.json not found")


def percentile(values, p=0.95):
    values = sorted(values)

    if not values:
        return None

    position = (len(values) - 1) * p
    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return values[lower]

    return (
        values[lower]
        + (values[upper] - values[lower]) * (position - lower)
    )


@app.post("/")
async def latency_metrics(request: Request):
    try:
        payload = await request.json()

        if not isinstance(payload, dict):
            return JSONResponse(
                {"error": "Request body must be a JSON object"},
                status_code=400,
            )

        regions = payload.get("regions", [])
        threshold_ms = float(payload.get("threshold_ms", 180))

        if not isinstance(regions, list) or not all(
            isinstance(region, str) for region in regions
        ):
            return JSONResponse(
                {"error": "'regions' must be a list of strings"},
                status_code=400,
            )

    except (ValueError, TypeError):
        return JSONResponse(
            {"error": "Invalid JSON or threshold_ms"},
            status_code=400,
        )

    try:
        telemetry = load_telemetry()
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return JSONResponse(
            {"error": f"Unable to load telemetry data: {error}"},
            status_code=500,
        )

    result = {}

    for region in regions:
        rows = [
            row for row in telemetry
            if row.get("region") == region
        ]

        if not rows:
            result[region] = {
                "avg_latency": None,
                "p95_latency": None,
                "avg_uptime": None,
                "breaches": 0,
            }
            continue

        latencies = [float(row["latency_ms"]) for row in rows]
        uptimes = [float(row["uptime_pct"]) for row in rows]

        result[region] = {
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": percentile(latencies, 0.95),
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(
                latency > threshold_ms for latency in latencies
            ),
        }

    return result

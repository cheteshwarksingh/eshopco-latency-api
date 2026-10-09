
import json
import math
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

# Allow requests from any origin, including POST and OPTIONS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)


def load_telemetry():
    possible_paths = [
        Path(__file__).resolve().parent.parent / "telemetry.json",
        Path(__file__).resolve().parent / "telemetry.json",
        Path.cwd() / "telemetry.json",
    ]

    for path in possible_paths:
        if path.is_file():
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)

    raise FileNotFoundError("telemetry.json not found")


def calculate_percentile(values, percentile=0.95):
    values = sorted(values)

    if not values:
        return None

    position = (len(values) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return values[lower]

    return (
        values[lower]
        + (values[upper] - values[lower])
        * (position - lower)
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

        if (
            not isinstance(regions, list)
            or not all(isinstance(region, str) for region in regions)
        ):
            return JSONResponse(
                {"error": "'regions' must be a list of strings"},
                status_code=400,
            )

        if not math.isfinite(threshold_ms):
            return JSONResponse(
                {"error": "threshold_ms must be a finite number"},
                status_code=400,
            )

    except (ValueError, TypeError):
        return JSONResponse(
            {"error": "Invalid JSON or threshold_ms"},
            status_code=400,
        )

    try:
        telemetry = load_telemetry()
    except (FileNotFoundError, json.JSONDecodeError):
        return JSONResponse(
            {"error": "Unable to load telemetry data"},
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

        latencies = [
            float(row["latency_ms"]) for row in rows
        ]
        uptimes = [
            float(row["uptime_pct"]) for row in rows
        ]

        result[region] = {
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": calculate_percentile(latencies),
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(
                latency > threshold_ms for latency in latencies
            ),
        }

    return result

import json
import math
import os
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

DATA_PATH = Path(__file__).resolve().parent.parent / "telemetry.json"
with DATA_PATH.open("r", encoding="utf-8") as f:
    TELEMETRY = json.load(f)


def percentile(values, p):
    """Linear-interpolated percentile (same convention as NumPy's default)."""
    values = sorted(values)
    if not values:
        return None
    position = (len(values) - 1) * p
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


@app.post("/")
async def latency_metrics(request: Request):
    try:
        payload = await request.json()
        regions = payload.get("regions", [])
        threshold_ms = float(payload.get("threshold_ms", 180))
        if not isinstance(regions, list) or not all(isinstance(r, str) for r in regions):
            return JSONResponse({"error": "'regions' must be a list of strings"}, status_code=400)
    except (ValueError, TypeError):
        return JSONResponse({"error": "Expected a JSON body with regions and threshold_ms"}, status_code=400)

    result = {}
    for region in regions:
        rows = [row for row in TELEMETRY if row.get("region") == region]
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
            "breaches": sum(value > threshold_ms for value in latencies),
        }

    return result

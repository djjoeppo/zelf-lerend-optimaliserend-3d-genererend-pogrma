import asyncio
from typing import Dict, Any, Optional
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .models import (
    SandboxConfig,
    MaterialProperties,
    MotorSpecs,
    OptimizationWeights,
    GAConfig,
    MOTOR_PRESETS,
    MATERIAL_PRESETS,
)
from .geometry import ConeGeometry
from .ga import ConeOptimizerGA


app = FastAPI(title="Luidsprekerconus Optimalisatie Studio", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OptimizationRequest(BaseModel):
    sandbox: SandboxConfig
    material: MaterialProperties
    motor: MotorSpecs
    weights: OptimizationWeights
    ga_config: GAConfig


class AppState:
    optimizer: Optional[ConeOptimizerGA] = None
    is_running: bool = False
    task: Optional[asyncio.Task] = None
    uploaded_flange_info: Optional[Dict[str, Any]] = None


state = AppState()


@app.get("/api/presets")
def get_presets():
    return {
        "motors": MOTOR_PRESETS,
        "materials": MATERIAL_PRESETS,
        "default_sandbox": SandboxConfig(),
        "default_weights": OptimizationWeights(),
        "default_ga_config": GAConfig(),
    }


async def run_optimization_loop():
    try:
        state.is_running = True
        opt = state.optimizer
        if not opt:
            return

        opt.initialize_population()

        for g in range(opt.config.total_generations):
            if not state.is_running:
                break
            opt.step_generation()
            # Korte sleep om CPU thread af te wisselen en realtime updates soepel te laten verlopen
            await asyncio.sleep(0.05)
    except Exception as e:
        print(f"Error during optimization loop: {e}")
    finally:
        state.is_running = False


@app.post("/api/optimization/start")
async def start_optimization(req: OptimizationRequest):
    if state.is_running:
        raise HTTPException(status_code=400, detail="Optimalisatie is al actief")

    state.optimizer = ConeOptimizerGA(
        sandbox=req.sandbox,
        material=req.material,
        motor=req.motor,
        weights=req.weights,
        ga_config=req.ga_config,
    )
    state.task = asyncio.create_task(run_optimization_loop())
    return {"status": "started"}


@app.post("/api/optimization/stop")
def stop_optimization():
    state.is_running = False
    return {"status": "stopped"}


@app.get("/api/optimization/status")
def get_status():
    if not state.optimizer:
        return {
            "is_running": False,
            "has_data": False,
            "current_gen": 0,
            "total_gen": 0,
            "phase": 1,
            "history": [],
            "best": None,
        }

    opt = state.optimizer
    best_data = opt.get_best_result_dict() if opt.best_individual else None

    return {
        "is_running": state.is_running,
        "has_data": True,
        "current_gen": opt.current_gen,
        "total_gen": opt.config.total_generations,
        "phase": opt.current_phase,
        "history": opt.generation_history,
        "best": best_data,
    }


@app.post("/api/evaluate-single")
def evaluate_single(req: OptimizationRequest):
    """
    Genereert een willekeurige of specifieke conus en evalueert deze direct
    voor snelle preview en inspectie zonder de volledige GA te starten.
    """
    cone = ConeGeometry.random_candidate(req.sandbox, req.material)
    from .acoustics import AcousticSimulation
    metrics = AcousticSimulation.evaluate_phase2(cone, req.motor)

    return {
        "is_valid": cone.is_valid,
        "validation_errors": cone.validation_errors,
        "metrics": metrics,
        "geometry": {
            "r_profile": [round(float(r), 2) for r in cone.r_profile],
            "z_profile": [round(float(z), 2) for z in cone.z_profile],
            "thickness_profile": [round(float(t), 2) for t in cone.thickness_profile],
            "collar_height_mm": cone.sandbox.collar_height_mm,
            "surround_flange_width_mm": cone.surround_flange_width_mm,
        }
    }


@app.get("/api/export-stl")
def export_best_stl():
    """
    Download het beste conusontwerp als STL-bestand.
    """
    if not state.optimizer or not state.optimizer.best_individual:
        # Als er nog geen GA is gedraaid, exporteer een standaard conus
        s = SandboxConfig()
        m = MATERIAL_PRESETS["PLA"]
        cone = ConeGeometry.random_candidate(s, m)
    else:
        cone = state.optimizer.best_individual.cone

    stl_bytes = cone.export_stl_bytes()
    return Response(
        content=stl_bytes,
        media_type="application/sla",
        headers={"Content-Disposition": 'attachment; filename="loudspeaker_cone_optimized.stl"'},
    )


@app.post("/api/flange/upload")
async def upload_custom_flange(file: UploadFile = File(...)):
    """
    Ondersteunt upload van een aangepast STL-bestand voor montageflenzen.
    Analyseert de afmetingen (bounding box) van de flensinterface.
    """
    contents = await file.read()
    try:
        import trimesh
        import io
        mesh = trimesh.load(io.BytesIO(contents), file_type='stl')
        bounds = mesh.bounds.tolist() if hasattr(mesh, 'bounds') else []
        extents = mesh.extents.tolist() if hasattr(mesh, 'extents') else []
        state.uploaded_flange_info = {
            "filename": file.filename,
            "size_bytes": len(contents),
            "bounds": bounds,
            "extents": extents,
            "outer_diameter_mm": round(float(extents[0]), 2) if len(extents) > 0 else 0.0,
            "height_mm": round(float(extents[2]), 2) if len(extents) > 2 else 0.0
        }
        return {"status": "success", "info": state.uploaded_flange_info}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Kon STL flens niet parsen: {str(e)}")


# Serveer gecompileerde React frontend als die aanwezig is
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_dist / "index.html"))

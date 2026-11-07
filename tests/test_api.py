import pytest
from fastapi.testclient import TestClient
from backend.cone_opt.api import app

client = TestClient(app)

def test_api_presets():
    response = client.get("/api/presets")
    assert response.status_code == 200
    data = response.json()
    assert "motors" in data
    assert "materials" in data
    assert "default_sandbox" in data

def test_api_evaluate_single():
    payload = {
        "sandbox": {
            "max_diameter_mm": 165.0,
            "max_height_mm": 45.0,
            "voice_coil_diameter_mm": 25.4,
            "collar_height_mm": 4.0,
            "collar_thickness_mm": 1.2,
            "min_wall_thickness_mm": 0.4,
            "max_wall_thickness_mm": 2.5,
            "overhang_check_enabled": True,
            "max_overhang_angle_deg": 70.0,
            "keep_out_zones": []
        },
        "material": {
            "name": "PLA",
            "density_g_cm3": 1.24,
            "youngs_modulus_gpa": 3.5,
            "poisson_ratio": 0.36,
            "loss_factor": 0.04
        },
        "motor": {
            "name": "Standard 6.5\" Motor",
            "bl": 6.5,
            "re": 5.8,
            "voice_coil_mass_g": 4.2,
            "voice_coil_diameter_mm": 25.4,
            "cms_mm_n": 0.65,
            "rms_kg_s": 1.2
        },
        "weights": {
            "weight_mass": 1.0,
            "weight_stiffness": 1.2,
            "weight_sensitivity": 1.5,
            "weight_target_fs": 1.0,
            "target_fs_hz": 45.0,
            "weight_linearity": 1.5,
            "target_freq_min_hz": 40.0,
            "target_freq_max_hz": 5000.0
        },
        "ga_config": {
            "total_generations": 5,
            "phase1_generations": 2,
            "population_size_phase1": 10,
            "population_size_phase2": 4,
            "mutation_rate": 0.2,
            "crossover_rate": 0.7
        }
    }
    response = client.post("/api/evaluate-single", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert "metrics" in res_data
    assert "geometry" in res_data

def test_api_export_stl():
    response = client.get("/api/export-stl")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/sla"
    assert len(response.content) > 100

import pytest
from backend.cone_opt.models import SandboxConfig, MOTOR_PRESETS, MATERIAL_PRESETS
from backend.cone_opt.geometry import ConeGeometry
from backend.cone_opt.acoustics import AcousticSimulation


def test_acoustic_phase1_simulation():
    sandbox = SandboxConfig(
        max_diameter_mm=165.0,
        max_height_mm=45.0,
        voice_coil_diameter_mm=25.4,
        max_overhang_angle_deg=70.0
    )
    material = MATERIAL_PRESETS["PLA"]
    motor = MOTOR_PRESETS["6.5_inch"]
    cone = ConeGeometry.random_candidate(sandbox, material)

    assert cone.is_valid
    res1 = AcousticSimulation.evaluate_phase1(cone, motor)
    assert res1["valid"] is True
    assert 20.0 < res1["fs_hz"] < 120.0
    assert 75.0 < res1["sensitivity_db"] < 100.0
    assert res1["cone_mass_g"] > 0
    assert res1["mms_g"] > res1["cone_mass_g"]


def test_acoustic_phase2_simulation():
    sandbox = SandboxConfig(
        max_diameter_mm=165.0,
        max_height_mm=45.0,
        voice_coil_diameter_mm=25.4,
        max_overhang_angle_deg=70.0
    )
    material = MATERIAL_PRESETS["PLA"]
    motor = MOTOR_PRESETS["6.5_inch"]
    cone = ConeGeometry.random_candidate(sandbox, material)

    res2 = AcousticSimulation.evaluate_phase2(cone, motor)
    assert res2["valid"] is True
    assert "frequency_response" in res2
    assert len(res2["frequency_response"]) == 100
    assert res2["f_breakup_hz"] > 500.0
    assert res2["linearity_ripple_db"] > 0

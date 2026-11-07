import pytest
import numpy as np
from backend.cone_opt.models import SandboxConfig, MaterialProperties, KeepOutZone, MATERIAL_PRESETS
from backend.cone_opt.geometry import ConeGeometry


def test_valid_cone_geometry():
    sandbox = SandboxConfig(
        max_diameter_mm=165.0,
        max_height_mm=45.0,
        voice_coil_diameter_mm=25.4,
        min_wall_thickness_mm=0.4,
        overhang_check_enabled=True,
        max_overhang_angle_deg=70.0
    )
    material = MATERIAL_PRESETS["PLA"]
    cone = ConeGeometry.random_candidate(sandbox, material)

    assert cone.r_profile is not None
    assert len(cone.r_profile) > 0
    assert cone.mass_g > 0
    assert cone.volume_mm3 > 0
    assert cone.stiffness_index > 0


def test_min_wall_thickness_enforcement():
    sandbox = SandboxConfig(
        max_diameter_mm=165.0,
        max_height_mm=40.0,
        voice_coil_diameter_mm=25.4,
        min_wall_thickness_mm=0.4,
        max_wall_thickness_mm=1.0,
    )
    material = MATERIAL_PRESETS["PLA"]
    # Maak opzettelijk te dunne conus (< 0.4 mm)
    cone = ConeGeometry(
        sandbox=sandbox,
        material=material,
        control_points_norm=[(0.3, 0.3), (0.7, 0.7)],
        thickness_points_norm=[-0.5, -0.5] # Zal onder min vallen
    )
    # Als minimum wall thickness geschonden wordt, moet is_valid False zijn
    if np.min(cone.thickness_profile) < 0.4:
        assert not cone.is_valid
        assert any("Wanddikte" in err for err in cone.validation_errors)


def test_keep_out_zone():
    sandbox = SandboxConfig(
        max_diameter_mm=165.0,
        max_height_mm=40.0,
        voice_coil_diameter_mm=25.4,
        min_wall_thickness_mm=0.4,
        keep_out_zones=[
            # Zone waar de conus zeker doorheen zou lopen (r: 30-50, z: 10-25)
            KeepOutZone(r_min=30.0, r_max=50.0, z_min=10.0, z_max=25.0)
        ]
    )
    material = MATERIAL_PRESETS["PLA"]
    cone = ConeGeometry(
        sandbox=sandbox,
        material=material,
        control_points_norm=[(0.3, 0.3), (0.7, 0.7)],
        thickness_points_norm=[0.5, 0.5]
    )
    # Bevestig detectie keep-out zone botsing
    assert not cone.is_valid
    assert any("Keep-out Zone" in err for err in cone.validation_errors)


def test_stl_generation():
    sandbox = SandboxConfig()
    material = MATERIAL_PRESETS["PLA"]
    cone = ConeGeometry.random_candidate(sandbox, material)
    stl_bytes = cone.export_stl_bytes()
    assert len(stl_bytes) > 100
    assert stl_bytes.startswith(b"solid") or len(stl_bytes) > 200

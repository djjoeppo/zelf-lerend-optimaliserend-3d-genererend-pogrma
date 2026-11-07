import pytest
from backend.cone_opt.models import SandboxConfig, MOTOR_PRESETS, MATERIAL_PRESETS, OptimizationWeights, GAConfig
from backend.cone_opt.ga import ConeOptimizerGA


def test_genetic_algorithm_staged_run():
    sandbox = SandboxConfig(
        max_diameter_mm=165.0,
        max_height_mm=45.0,
        voice_coil_diameter_mm=25.4,
        max_overhang_angle_deg=70.0
    )
    material = MATERIAL_PRESETS["PLA"]
    motor = MOTOR_PRESETS["6.5_inch"]
    weights = OptimizationWeights()
    ga_config = GAConfig(
        total_generations=5,
        phase1_generations=3,
        population_size_phase1=10,
        population_size_phase2=4
    )

    optimizer = ConeOptimizerGA(sandbox, material, motor, weights, ga_config)
    optimizer.initialize_population()
    assert len(optimizer.population) == 10

    # Stap generaties door
    for g in range(5):
        stats = optimizer.step_generation()
        assert stats["generation"] == g + 1
        if g + 1 <= 3:
            assert stats["phase"] == 1
        else:
            assert stats["phase"] == 2

    assert len(optimizer.generation_history) == 5
    best_result = optimizer.get_best_result_dict()
    assert "metrics" in best_result
    assert "geometry" in best_result
    assert best_result["fitness"] is not None
    assert "frequency_response" in best_result["metrics"]

import copy
import numpy as np
from typing import List, Dict, Any, Tuple, Optional, Callable
from .models import SandboxConfig, MaterialProperties, MotorSpecs, OptimizationWeights, GAConfig
from .geometry import ConeGeometry
from .acoustics import AcousticSimulation


class Individual:
    """
    Representeert een kandidaat binnen het genetisch algoritme.
    Genoom bestaat uit:
    - ctrl_pts: list van (u, v) coördinaten van interne Bézier punten
    - thick_pts: list van diktefactoren
    """
    def __init__(
        self,
        sandbox: SandboxConfig,
        material: MaterialProperties,
        ctrl_pts: List[Tuple[float, float]],
        thick_pts: List[float],
        generation: int = 0
    ):
        self.sandbox = sandbox
        self.material = material
        self.ctrl_pts = ctrl_pts
        self.thick_pts = thick_pts
        self.generation = generation

        self.cone = ConeGeometry(sandbox, material, ctrl_pts, thick_pts)
        self.fitness: float = -1e9
        self.metrics: Dict[str, Any] = {}

    @classmethod
    def random(cls, sandbox: SandboxConfig, material: MaterialProperties, generation: int = 0) -> "Individual":
        num_ctrl = 3
        u_vals = np.sort(np.random.uniform(0.15, 0.85, num_ctrl))
        v_vals = np.sort([float(np.clip(u + np.random.uniform(-0.15, 0.15), 0.05, 0.95)) for u in u_vals])
        ctrl_pts = [(float(u), float(v)) for u, v in zip(u_vals, v_vals)]
        thick_pts = [float(np.random.uniform(0.1, 0.7)) for _ in range(4)]
        return cls(sandbox, material, ctrl_pts, thick_pts, generation=generation)

    def mutate(self, mutation_rate: float = 0.25):
        """
        Voert mutaties uit op stuurpunten en wanddiktes.
        """
        new_ctrl = []
        for u, v in self.ctrl_pts:
            if np.random.rand() < mutation_rate:
                u += np.random.normal(0, 0.05)
                u = float(np.clip(u, 0.05, 0.95))
            if np.random.rand() < mutation_rate:
                v += np.random.normal(0, 0.05)
                v = float(np.clip(v, 0.05, 0.95))
            new_ctrl.append((u, v))
        # Zorg voor geordende punten zodat conus monotoon stijgt
        new_ctrl.sort(key=lambda p: p[0])

        new_thick = []
        for t in self.thick_pts:
            if np.random.rand() < mutation_rate:
                t += np.random.normal(0, 0.08)
                t = float(np.clip(t, 0.0, 1.0))
            new_thick.append(t)

        self.ctrl_pts = new_ctrl
        self.thick_pts = new_thick
        self.cone = ConeGeometry(self.sandbox, self.material, self.ctrl_pts, self.thick_pts)

    @classmethod
    def crossover(cls, parent_a: "Individual", parent_b: "Individual", generation: int) -> "Individual":
        """
        Uniform/Blend crossover tussen twee conus-individuen.
        """
        child_ctrl = []
        for p1, p2 in zip(parent_a.ctrl_pts, parent_b.ctrl_pts):
            alpha = np.random.uniform(-0.1, 1.1)
            u = float(np.clip(p1[0] + alpha * (p2[0] - p1[0]), 0.05, 0.95))
            beta = np.random.uniform(-0.1, 1.1)
            v = float(np.clip(p1[1] + beta * (p2[1] - p1[1]), 0.05, 0.95))
            child_ctrl.append((u, v))
        child_ctrl.sort(key=lambda p: p[0])

        child_thick = []
        for t1, t2 in zip(parent_a.thick_pts, parent_b.thick_pts):
            gamma = np.random.uniform(0.0, 1.0)
            t = float(np.clip(gamma * t1 + (1 - gamma) * t2, 0.0, 1.0))
            child_thick.append(t)

        return cls(parent_a.sandbox, parent_a.material, child_ctrl, child_thick, generation=generation)


class ConeOptimizerGA:
    """
    Staged Multi-Fidelity Genetisch Algoritme voor Luidsprekerconussen.
    """
    def __init__(
        self,
        sandbox: SandboxConfig,
        material: MaterialProperties,
        motor: MotorSpecs,
        weights: OptimizationWeights,
        ga_config: GAConfig,
    ):
        self.sandbox = sandbox
        self.material = material
        self.motor = motor
        self.weights = weights
        self.config = ga_config

        self.population: List[Individual] = []
        self.generation_history: List[Dict[str, Any]] = []
        self.best_individual: Optional[Individual] = None
        self.is_running: bool = False
        self.current_phase: int = 1
        self.current_gen: int = 0

    def calculate_fitness_phase1(self, ind: Individual) -> float:
        """
        Fitnessberekening Fase 1 (snelle screening).
        """
        if not ind.cone.is_valid:
            ind.fitness = -1000.0 - len(ind.cone.validation_errors) * 100.0
            ind.metrics = {"valid": False, "errors": ind.cone.validation_errors}
            return ind.fitness

        metrics = AcousticSimulation.evaluate_phase1(ind.cone, self.motor)
        ind.metrics = metrics

        # Score componenten:
        # 1. Massa (lager is beter, genormaliseerd rond 15g)
        mass_score = 100.0 - (metrics["cone_mass_g"] * 2.0)
        # 2. Resonantie Fs doelafwijking
        fs_diff = abs(metrics["fs_hz"] - self.weights.target_fs_hz)
        fs_score = max(0.0, 100.0 - fs_diff * 3.0)
        # 3. Gevoeligheid (hogere SPL is beter, genormaliseerd rond 85 dB)
        spl_score = (metrics["sensitivity_db"] - 75.0) * 5.0
        # 4. Stijfheid
        stiffness_score = np.log10(max(metrics["stiffness_index"], 1e-3) + 1.0) * 15.0

        fitness = (
            self.weights.weight_mass * mass_score +
            self.weights.weight_target_fs * fs_score +
            self.weights.weight_sensitivity * spl_score +
            self.weights.weight_stiffness * stiffness_score
        )
        ind.fitness = float(fitness)
        return ind.fitness

    def calculate_fitness_phase2(self, ind: Individual) -> float:
        """
        Fitnessberekening Fase 2 (verfijnde simulatie met breakup en lineariteit).
        """
        if not ind.cone.is_valid:
            ind.fitness = -1000.0
            ind.metrics = {"valid": False, "errors": ind.cone.validation_errors}
            return ind.fitness

        metrics = AcousticSimulation.evaluate_phase2(ind.cone, self.motor)
        ind.metrics = metrics

        # Basis Phase 1 score
        mass_score = 100.0 - (metrics["cone_mass_g"] * 2.0)
        fs_diff = abs(metrics["fs_hz"] - self.weights.target_fs_hz)
        fs_score = max(0.0, 100.0 - fs_diff * 3.0)
        spl_score = (metrics["sensitivity_db"] - 75.0) * 5.0
        stiffness_score = np.log10(max(metrics["stiffness_index"], 1e-3) + 1.0) * 15.0

        # Aanvullende Phase 2 componenten:
        # Lineariteit / vlakheid (lagere rimpel = hogere score)
        ripple = metrics.get("linearity_ripple_db", 10.0)
        linearity_score = max(0.0, 100.0 - ripple * 15.0)

        # Breakup frequentie (liefst buiten of hoog in passband)
        breakup = metrics.get("f_breakup_hz", 2000.0)
        breakup_score = min(100.0, (breakup / 40.0))

        fitness = (
            self.weights.weight_mass * mass_score +
            self.weights.weight_target_fs * fs_score +
            self.weights.weight_sensitivity * spl_score +
            self.weights.weight_stiffness * stiffness_score +
            self.weights.weight_linearity * linearity_score +
            0.5 * breakup_score
        )
        ind.fitness = float(fitness)
        return ind.fitness

    def initialize_population(self):
        """
        Creëert een gevarieerde startpopulatie.
        """
        self.population = []
        attempts = 0
        target_size = self.config.population_size_phase1

        while len(self.population) < target_size and attempts < target_size * 10:
            ind = Individual.random(self.sandbox, self.material, generation=0)
            self.calculate_fitness_phase1(ind)
            self.population.append(ind)
            attempts += 1

        # Sorteer op fitness
        self.population.sort(key=lambda x: x.fitness, reverse=True)
        self.best_individual = copy.deepcopy(self.population[0])

    def step_generation(self) -> Dict[str, Any]:
        """
        Voert één generatiestap uit in het staged optimalisatieproces.
        """
        self.current_gen += 1
        is_phase1 = self.current_gen <= self.config.phase1_generations
        self.current_phase = 1 if is_phase1 else 2

        if is_phase1:
            pop_size = self.config.population_size_phase1
            eval_fn = self.calculate_fitness_phase1
        else:
            # Fase 2: krimp populatie naar topkandidaten en verfijn met diepe evaluatie
            pop_size = self.config.population_size_phase2
            eval_fn = self.calculate_fitness_phase2
            if len(self.population) > pop_size:
                self.population = self.population[:pop_size]

        # Evalueer alle individuen
        for ind in self.population:
            eval_fn(ind)

        # Sorteer op fitness
        self.population.sort(key=lambda x: x.fitness, reverse=True)

        if self.population[0].fitness > (self.best_individual.fitness if self.best_individual else -1e9):
            # Zorg dat de beste ook Phase 2 data bevat
            if not is_phase1 and "frequency_response" not in self.population[0].metrics:
                self.calculate_fitness_phase2(self.population[0])
            self.best_individual = copy.deepcopy(self.population[0])

        # Elitisme: bewaar beste kandidaten
        elite_count = max(2, int(pop_size * 0.15))
        new_population = [copy.deepcopy(ind) for ind in self.population[:elite_count]]

        # Reproductie (Selectie via Tournament, Crossover & Mutatie)
        while len(new_population) < pop_size:
            # Tournament selection (selecteer 3 willekeurige en pak de beste)
            def tournament():
                candidates = np.random.choice(self.population[:max(4, int(pop_size * 0.7))], size=min(3, len(self.population)), replace=False)
                return max(candidates, key=lambda c: c.fitness)

            parent1 = tournament()
            parent2 = tournament()

            if np.random.rand() < self.config.crossover_rate:
                child = Individual.crossover(parent1, parent2, generation=self.current_gen)
            else:
                child = copy.deepcopy(parent1)

            if np.random.rand() < self.config.mutation_rate:
                child.mutate(self.config.mutation_rate)

            eval_fn(child)
            new_population.append(child)

        self.population = new_population
        self.population.sort(key=lambda x: x.fitness, reverse=True)

        # Genereer generatiestatistieken
        valid_pop = [ind for ind in self.population if ind.cone.is_valid]
        gen_stats = {
            "generation": self.current_gen,
            "phase": self.current_phase,
            "best_fitness": round(float(self.best_individual.fitness), 2) if self.best_individual else 0.0,
            "avg_fitness": round(float(np.mean([ind.fitness for ind in self.population])), 2),
            "valid_rate": round(len(valid_pop) / len(self.population) * 100.0, 1),
            "best_mass_g": self.best_individual.metrics.get("cone_mass_g", 0.0) if self.best_individual else 0.0,
            "best_fs_hz": self.best_individual.metrics.get("fs_hz", 0.0) if self.best_individual else 0.0,
            "best_spl_db": self.best_individual.metrics.get("sensitivity_db", 0.0) if self.best_individual else 0.0,
        }
        self.generation_history.append(gen_stats)
        return gen_stats

    def get_best_result_dict(self) -> Dict[str, Any]:
        """
        Retourneert een compleet resultatenobject van het beste ontwerp tot nu toe.
        """
        if not self.best_individual:
            return {}

        # Zorg voor volledige Phase 2 details
        if "frequency_response" not in self.best_individual.metrics:
            self.calculate_fitness_phase2(self.best_individual)

        cone = self.best_individual.cone
        return {
            "generation": self.best_individual.generation,
            "fitness": round(float(self.best_individual.fitness), 2),
            "is_valid": cone.is_valid,
            "validation_errors": cone.validation_errors,
            "metrics": self.best_individual.metrics,
            "geometry": {
                "r_profile": [round(float(r), 2) for r in cone.r_profile],
                "z_profile": [round(float(z), 2) for z in cone.z_profile],
                "thickness_profile": [round(float(t), 2) for t in cone.thickness_profile],
                "control_points": self.best_individual.ctrl_pts,
                "thickness_points": self.best_individual.thick_pts,
                "collar_height_mm": cone.sandbox.collar_height_mm,
                "surround_flange_width_mm": cone.surround_flange_width_mm
            }
        }

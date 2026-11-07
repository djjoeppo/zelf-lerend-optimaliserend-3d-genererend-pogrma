from typing import List, Optional
from pydantic import BaseModel, Field


class MaterialProperties(BaseModel):
    name: str = "PLA"
    density_g_cm3: float = Field(1.24, description="Dichtheid in g/cm3")
    youngs_modulus_gpa: float = Field(3.5, description="Elasticiteitsmodulus in GPa")
    poisson_ratio: float = Field(0.36, description="Poissonverhouding")
    loss_factor: float = Field(0.04, description="Mechanische dempingsfactor (damping)")


# Presets voor 3D-print materialen
MATERIAL_PRESETS = {
    "PLA": MaterialProperties(name="PLA", density_g_cm3=1.24, youngs_modulus_gpa=3.5, poisson_ratio=0.36, loss_factor=0.04),
    "PETG": MaterialProperties(name="PETG", density_g_cm3=1.27, youngs_modulus_gpa=2.1, poisson_ratio=0.38, loss_factor=0.05),
    "ABS": MaterialProperties(name="ABS", density_g_cm3=1.04, youngs_modulus_gpa=2.3, poisson_ratio=0.35, loss_factor=0.045),
    "LW-PLA": MaterialProperties(name="LW-PLA", density_g_cm3=0.60, youngs_modulus_gpa=1.4, poisson_ratio=0.33, loss_factor=0.06),
}


class KeepOutZone(BaseModel):
    r_min: float = Field(..., description="Minimale straal (mm)")
    r_max: float = Field(..., description="Maximale straal (mm)")
    z_min: float = Field(..., description="Minimale Z hoogte (mm)")
    z_max: float = Field(..., description="Maximale Z hoogte (mm)")


class SandboxConfig(BaseModel):
    max_diameter_mm: float = Field(165.0, description="Maximale conusdiameter in mm (bijv. 6.5 inch)")
    max_height_mm: float = Field(45.0, description="Maximale conusdiepte/hoogte in mm")
    voice_coil_diameter_mm: float = Field(25.4, description="Spreekspoeldiameter in mm (bijv. 1 inch)")
    collar_height_mm: float = Field(4.0, description="Hoogte van spreekspoel montagevlakje (collar) in mm")
    collar_thickness_mm: float = Field(1.2, description="Dikte van spreekspoel collar in mm")
    min_wall_thickness_mm: float = Field(0.4, description="Harde minimale wanddikte in mm (standaard 0.4 mm)")
    max_wall_thickness_mm: float = Field(2.5, description="Maximale wanddikte in mm")
    overhang_check_enabled: bool = Field(True, description="Harde overhangcontrole in-/uitschakelen")
    max_overhang_angle_deg: float = Field(60.0, description="Maximale toegestane overhanghoek t.o.v. verticaal (graden)")
    keep_out_zones: List[KeepOutZone] = Field(default_factory=list, description="Zones waar geen conusmateriaal mag komen")


class MotorSpecs(BaseModel):
    name: str = "Standard 6.5\" Motor"
    bl: float = Field(6.5, description="Krachtfactor Bl in N/A (T*m)")
    re: float = Field(5.8, description="Gelijkstroomweerstand spreekspoel Re in Ohm")
    voice_coil_mass_g: float = Field(4.2, description="Massa spreekspoel + drager Mvc in gram")
    voice_coil_diameter_mm: float = Field(25.4, description="Spreekspoel diameter in mm")
    cms_mm_n: float = Field(0.65, description="Mechanische compliantie ophanging (spider+surround) Cms in mm/N")
    rms_kg_s: float = Field(1.2, description="Mechanische dempingsweerstand Rms in kg/s")


MOTOR_PRESETS = {
    "4_inch": MotorSpecs(
        name="Compact 4\" Midwoofer",
        bl=4.5,
        re=4.0,
        voice_coil_mass_g=2.1,
        voice_coil_diameter_mm=20.4,
        cms_mm_n=0.9,
        rms_kg_s=0.8
    ),
    "6.5_inch": MotorSpecs(
        name="Standard 6.5\" Woofer",
        bl=6.5,
        re=5.8,
        voice_coil_mass_g=4.2,
        voice_coil_diameter_mm=25.4,
        cms_mm_n=0.65,
        rms_kg_s=1.2
    ),
    "8_inch": MotorSpecs(
        name="Powerful 8\" Sub/Woofer",
        bl=9.8,
        re=6.2,
        voice_coil_mass_g=8.5,
        voice_coil_diameter_mm=38.5,
        cms_mm_n=0.45,
        rms_kg_s=1.8
    )
}


class OptimizationWeights(BaseModel):
    weight_mass: float = Field(1.0, description="Prioriteit voor licht conusgewicht (lagere massa)")
    weight_stiffness: float = Field(1.2, description="Prioriteit voor mechanische stijfheid")
    weight_sensitivity: float = Field(1.5, description="Prioriteit voor hoge basisgevoeligheid (SPL)")
    weight_target_fs: float = Field(1.0, description="Prioriteit voor het halen van gewenste Fs")
    target_fs_hz: float = Field(45.0, description="Gewenste theoretische Fs in Hz")
    weight_linearity: float = Field(1.5, description="Prioriteit voor vlakke free-air frequentierespons")
    target_freq_min_hz: float = Field(40.0, description="Minimale frequentie van doelspectrum")
    target_freq_max_hz: float = Field(5000.0, description="Maximale frequentie van doelspectrum")


class GAConfig(BaseModel):
    total_generations: int = Field(40, description="Totaal aantal generaties")
    phase1_generations: int = Field(15, description="Aantal generaties voor Fase 1 (snelle screening)")
    population_size_phase1: int = Field(30, description="Populatiegrootte in Fase 1")
    population_size_phase2: int = Field(12, description="Aantal geselecteerde topontwerpen voor verfijning in Fase 2")
    mutation_rate: float = Field(0.2, description="Kans op genmutatie")
    crossover_rate: float = Field(0.7, description="Kans op crossover")

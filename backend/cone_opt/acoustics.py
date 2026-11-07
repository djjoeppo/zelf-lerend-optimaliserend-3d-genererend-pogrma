import numpy as np
from typing import Dict, Any, Tuple, List
from .models import MotorSpecs, MaterialProperties
from .geometry import ConeGeometry


class AcousticSimulation:
    """
    Multi-Fidelity Akoestische en Mechanische simulatie in Free-Air:

    Fase 1: Snelle screening
    - Lumped parameter zuigermodel (rigid piston electro-mechanical model)
    - Resonantiefrequentie Fs = 1 / (2 * pi * sqrt(Mms * Cms))
    - Mms = M_vc + M_cone + 2 * M_air (free-air stralingsmassa)
    - Geschatte referentiegevoeligheid (SPL @ 1W / 1m in dB)
    - Conusmassa en geometrische stijfheid

    Fase 2: Verfijning (Multi-ring breakup & elastische schaalmodi)
    - Radiale en axiale golfvoortplanting door conuswand
    - Bepaling van breakup-resonanties (eerste buigmodus / breakup frequency)
    - Modellering van frequentierespons (SPL vs frequentie van 20 Hz tot 20 kHz)
    - Analyse van resonantiepieken en lineariteit/vlakheid
    """
    RHO_AIR = 1.204   # kg/m^3 (luchtdichtheid bij 20 deg C)
    C_AIR = 343.0     # m/s (geluidssnelheid)

    @classmethod
    def evaluate_phase1(cls, cone: ConeGeometry, motor: MotorSpecs) -> Dict[str, Any]:
        """
        Snelle screening (Lumped-parameter model).
        """
        if not cone.is_valid:
            return {
                "valid": False,
                "errors": cone.validation_errors,
                "mms_g": float('inf'),
                "fs_hz": 0.0,
                "sensitivity_db": 0.0,
                "cone_mass_g": float('inf'),
                "stiffness_index": 0.0,
            }

        # Conus effectief oppervlak Sd (m^2)
        r_outer_m = (cone.sandbox.max_diameter_mm / 2.0) * 1e-3
        r_inner_m = (cone.sandbox.voice_coil_diameter_mm / 2.0) * 1e-3
        # Effectieve akoestische zuigerstraal a_eff (circa conusrand minus half surround)
        a_eff_m = r_outer_m * 0.95
        sd_m2 = np.pi * (a_eff_m ** 2)

        # Luchtmassa M_air in vrije lucht (beide kanten van onbegrensde zuiger: 2 * 8/3 * rho * a^3)
        m_air_kg = 2.0 * (8.0 / (3.0 * np.pi)) * cls.RHO_AIR * (a_eff_m ** 3)
        m_air_g = m_air_kg * 1000.0

        # Totale bewegende massa Mms = M_cone + M_vc + M_air
        mms_g = cone.mass_g + motor.voice_coil_mass_g + m_air_g
        mms_kg = mms_g * 1e-3

        # Resonantiefrequentie Fs = 1 / (2 * pi * sqrt(Mms * Cms))
        # Cms is in mm/N -> omrekenen naar m/N (1e-3)
        cms_m_n = motor.cms_mm_n * 1e-3
        fs_hz = 1.0 / (2.0 * np.pi * np.sqrt(mms_kg * cms_m_n))

        # Geschatte basisgevoeligheid (SPL dB @ 1W, 1m in halve ruimte / free air referentie)
        # eta_0 = (rho_air * Bl^2 * Sd^2) / (2 * pi * c_air * Re * Mms^2)
        # SPL_1w_1m = 112 + 10 * log10(eta_0)
        bl = motor.bl
        re = motor.re
        eta_0 = (cls.RHO_AIR * (bl ** 2) * (sd_m2 ** 2)) / (2.0 * np.pi * cls.C_AIR * re * (mms_kg ** 2))
        eta_0 = max(eta_0, 1e-8) # prevent log(0)
        sensitivity_db = 112.0 + 10.0 * np.log10(eta_0)

        # Q-factoren (Qms, Qes, Qts)
        omega_s = 2.0 * np.pi * fs_hz
        qms = (omega_s * mms_kg) / motor.rms_kg_s
        qes = (omega_s * mms_kg * re) / (bl ** 2)
        qts = (qms * qes) / (qms + qes)

        return {
            "valid": True,
            "errors": [],
            "cone_mass_g": round(cone.mass_g, 2),
            "mms_g": round(mms_g, 2),
            "fs_hz": round(fs_hz, 1),
            "sensitivity_db": round(sensitivity_db, 1),
            "qts": round(qts, 2),
            "qes": round(qes, 2),
            "qms": round(qms, 2),
            "stiffness_index": round(cone.stiffness_index, 2),
        }

    @classmethod
    def evaluate_phase2(cls, cone: ConeGeometry, motor: MotorSpecs) -> Dict[str, Any]:
        """
        Uitgebreide simulatie (Fase 2):
        - Berekent gedetailleerde akoestische frequentierespons (SPL over 20 - 20000 Hz)
        - Berekent conus breakup frequentie f_breakup
        - Evalueert lineariteit (standaardafwijking in passband)
        """
        res1 = cls.evaluate_phase1(cone, motor)
        if not res1["valid"]:
            return res1

        mms_kg = res1["mms_g"] * 1e-3
        cms_m_n = motor.cms_mm_n * 1e-3
        rms = motor.rms_kg_s
        bl = motor.bl
        re = motor.re
        fs = res1["fs_hz"]

        # Materiaaleigenschappen
        youngs_pa = cone.material.youngs_modulus_gpa * 1e9
        density_kg_m3 = cone.material.density_g_cm3 * 1000.0
        c_sound_cone = np.sqrt(youngs_pa / density_kg_m3) # akoestische golfsnelheid in conusmateriaal

        # Breakup frequentie f_breakup:
        # Golflengte in conuswand komt overeen met conusprofiel-slaglengte (apex naar rim)
        dr = np.diff(cone.r_profile)
        dz = np.diff(cone.z_profile)
        slant_length_m = float(np.sum(np.sqrt(dr**2 + dz**2))) * 1e-3
        # Conuskromming en diepte verhogen breakup frequentie t.o.v. vlakke schijf
        cone_depth_m = (np.max(cone.z_profile) - np.min(cone.z_profile)) * 1e-3
        flaring_factor = 1.0 + 1.8 * (cone_depth_m / slant_length_m)

        f_breakup = (c_sound_cone / (2.0 * slant_length_m)) * flaring_factor
        # Eerste resonantie piek / dip zone
        f_breakup = float(np.clip(f_breakup, 800.0, 12000.0))

        # Frequentierespons berekening
        freqs = np.geomspace(20.0, 20000.0, 100)
        omegas = 2.0 * np.pi * freqs

        # Mechanische impedantie van ophanging en massa
        z_mech = rms + 1j * (omegas * mms_kg - 1.0 / (omegas * cms_m_n))
        # Totale elektrische impedantie inclusief motie-impedantie
        z_mot = (bl ** 2) / z_mech
        z_elec = re + z_mot

        # Conus conische schaal breakup filterfunctie
        # Boven f_breakup ontstaan buigmodi met pieken en dalen, gedempt door cone.material.loss_factor
        loss = cone.material.loss_factor
        # Modellering van conus-transferfunctie H_cone(f)
        ratio = freqs / f_breakup
        breakup_peaks = (
            1.0
            + 0.6 * np.exp(-((np.log(freqs) - np.log(f_breakup)) ** 2) / (2 * (0.25 ** 2))) / (loss * 15.0)
            - 0.4 * np.exp(-((np.log(freqs) - np.log(f_breakup * 1.4)) ** 2) / (2 * (0.2 ** 2)))
            + 0.3 * np.exp(-((np.log(freqs) - np.log(f_breakup * 2.2)) ** 2) / (2 * (0.3 ** 2)))
        )

        # Free-air versnelling a(omega) = F / Z_mech = (Bl * I) / Z_mech
        # Spanning U = 2.83 V (1W bij 8 ohm referentie)
        v_in = np.sqrt(8.0 * 1.0)
        current = v_in / np.abs(z_elec)
        force = bl * current
        velocity = force / np.abs(z_mech)
        acceleration = omegas * velocity

        # Druk P_freeair = (rho * Sd * a) / (4 * pi * r_dist)
        r_outer_m = (cone.sandbox.max_diameter_mm / 2.0) * 1e-3
        sd_m2 = np.pi * ((r_outer_m * 0.95) ** 2)
        p_spl = (cls.RHO_AIR * sd_m2 * acceleration) / (4.0 * np.pi * 1.0)
        p_spl = p_spl * breakup_peaks

        spl_curve = 20.0 * np.log10(np.maximum(p_spl / 20e-6, 1e-3))
        # Beperk curve binnen realistische grenzen
        spl_curve = np.clip(spl_curve, 40.0, 115.0)

        # Bepaal lineariteit (rimpel in passband tussen 200 Hz en 4000 Hz)
        passband_idx = (freqs >= 200.0) & (freqs <= 4000.0)
        spl_passband = spl_curve[passband_idx]
        linearity_ripple_db = float(np.std(spl_passband)) if len(spl_passband) > 0 else 10.0

        res2 = dict(res1)
        res2.update({
            "f_breakup_hz": round(f_breakup, 1),
            "linearity_ripple_db": round(linearity_ripple_db, 2),
            "frequency_response": [
                {"freq": round(float(f), 1), "spl": round(float(spl), 1)}
                for f, spl in zip(freqs, spl_curve)
            ]
        })
        return res2

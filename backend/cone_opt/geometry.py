import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from .models import SandboxConfig, MaterialProperties, KeepOutZone


class ConeGeometry:
    """
    Representeert een parametrisch conusprofiel opgebouwd uit:
    - Spreekspoelmontagevlak (collar/cilinder interface)
    - Conusprofiel beschreven door Bézier kromming tussen spreekspoel en buitenrand
    - Wanddikteverdeling t(r)
    - Optionele montageflens aan de buitenrand
    """
    def __init__(
        self,
        sandbox: SandboxConfig,
        material: MaterialProperties,
        control_points_norm: List[Tuple[float, float]], # (u, v) normalized control points in [0, 1]
        thickness_points_norm: List[float],             # normalized thickness factors [0, 1]
        surround_flange_width_mm: float = 6.0,
        surround_flange_thickness_mm: float = 1.0,
    ):
        self.sandbox = sandbox
        self.material = material
        self.control_points_norm = control_points_norm
        self.thickness_points_norm = thickness_points_norm
        self.surround_flange_width_mm = surround_flange_width_mm
        self.surround_flange_thickness_mm = surround_flange_thickness_mm

        # Bepaal profielpunten
        self.r_profile, self.z_profile, self.thickness_profile = self._generate_profile()
        self.is_valid, self.validation_errors = self._validate_manufacturability()

        if self.is_valid:
            self.volume_mm3, self.mass_g, self.stiffness_index = self._calculate_physical_properties()
        else:
            self.volume_mm3 = 0.0
            self.mass_g = float('inf')
            self.stiffness_index = 0.0

    @classmethod
    def random_candidate(cls, sandbox: SandboxConfig, material: MaterialProperties, max_tries: int = 20) -> "ConeGeometry":
        # Genereer controlepunten die monotoniciteit respecteren en natuurlijk conisch profiel vormen
        for _ in range(max_tries):
            num_ctrl = 3
            ctrl_pts = []
            # Bouw gesorteerde u en v op zodat r en z monotoon stijgen
            u_vals = np.sort(np.random.uniform(0.15, 0.85, num_ctrl))
            # v waarden dicht bij de rechte conus diagonaal (v ~ u) met lichte kromming (flared of curved)
            v_vals = np.sort([float(np.clip(u + np.random.uniform(-0.08, 0.08), 0.05, 0.95)) for u in u_vals])
            for u, v in zip(u_vals, v_vals):
                ctrl_pts.append((float(u), float(v)))

            # Diktefactoren op 4 posities langs conus (taps toelopend of gelijkmatig)
            thick_pts = [float(np.random.uniform(0.1, 0.7)) for _ in range(4)]
            cand = cls(sandbox, material, ctrl_pts, thick_pts)
            if cand.is_valid:
                return cand

        # Fallback op rechte conus
        return cls(sandbox, material, [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75)], [0.3, 0.3, 0.3, 0.3])

    def _generate_profile(self, num_samples: int = 50) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Genereert de r(s), z(s) en t(s) coördinaten van de conuswand
        inclusief de voice coil collar en surround flange.
        """
        r_inner = self.sandbox.voice_coil_diameter_mm / 2.0
        r_outer = self.sandbox.max_diameter_mm / 2.0 - self.surround_flange_width_mm
        h_max = self.sandbox.max_height_mm

        # Controlepunten in fysieke coördinaten
        # Startpunt conuswand direct na collar
        p_start = np.array([r_inner, self.sandbox.collar_height_mm])
        p_end = np.array([r_outer, h_max])

        pts = [p_start]
        for u, v in self.control_points_norm:
            r = r_inner + u * (r_outer - r_inner)
            z = self.sandbox.collar_height_mm + v * (h_max - self.sandbox.collar_height_mm)
            pts.append(np.array([r, z]))
        pts.append(p_end)
        pts = np.array(pts)

        # Bézier curve evaluatie
        t = np.linspace(0.0, 1.0, num_samples)
        curve_pts = np.zeros((num_samples, 2))
        n = len(pts) - 1
        for i, pt in enumerate(pts):
            from scipy.special import comb
            binom = comb(n, i)
            poly = binom * (t ** i) * ((1 - t) ** (n - i))
            curve_pts += np.outer(poly, pt)

        r_cone = curve_pts[:, 0]
        z_cone = curve_pts[:, 1]

        # Wanddikte berekenen via interpolatie
        min_th = self.sandbox.min_wall_thickness_mm
        max_th = self.sandbox.max_wall_thickness_mm
        thick_t = np.linspace(0.0, 1.0, len(self.thickness_points_norm))
        interp_thick = np.interp(t, thick_t, self.thickness_points_norm)
        t_cone = min_th + interp_thick * (max_th - min_th)

        # Toevoegen van Voice Coil Collar aan begin
        # Collar is een cilinder/vlakje aan r_inner met z van 0 tot collar_height
        collar_samples = 5
        r_collar = np.full(collar_samples, r_inner)
        z_collar = np.linspace(0, self.sandbox.collar_height_mm, collar_samples)
        t_collar = np.full(collar_samples, self.sandbox.collar_thickness_mm)

        # Toevoegen van Surround Flange aan conusrand
        # Flens is een vlakje van r_outer naar r_outer + flange_width op hoogte h_max
        flange_samples = 5
        r_flange = np.linspace(r_outer, r_outer + self.surround_flange_width_mm, flange_samples)
        z_flange = np.full(flange_samples, h_max)
        t_flange = np.full(flange_samples, self.surround_flange_thickness_mm)

        # Assembleer hele profiel
        r_all = np.concatenate([r_collar, r_cone, r_flange])
        z_all = np.concatenate([z_collar, z_cone, z_flange])
        t_all = np.concatenate([t_collar, t_cone, t_flange])

        return r_all, z_all, t_all

    def _validate_manufacturability(self) -> Tuple[bool, List[str]]:
        """
        Controleert alle harde maakbaarheidseisen:
        - Minimale wanddikte >= min_wall_thickness_mm
        - Sandbox overschrijding (radius, hoogte)
        - Overhangcontrole (hellingshoek t.o.v. printbed/verticaal)
        - Keep-out zones (botsingsvermijding)
        - Monotoniciteit van de straal (geen ondersnijdingen / rare zelfkruisingen)
        """
        errors = []

        # 1. Minimale wanddikte
        min_th = float(np.min(self.thickness_profile))
        if min_th < (self.sandbox.min_wall_thickness_mm - 1e-4):
            errors.append(f"Wanddikte ({min_th:.2f} mm) is dunner dan harde minimum ({self.sandbox.min_wall_thickness_mm:.2f} mm)")

        # 2. Sandbox grenzen
        max_r_allowed = self.sandbox.max_diameter_mm / 2.0
        if np.max(self.r_profile) > max_r_allowed + 1e-3:
            errors.append(f"Maximale straal ({np.max(self.r_profile):.1f} mm) overschrijdt sandbox straal ({max_r_allowed:.1f} mm)")

        if np.max(self.z_profile) > self.sandbox.max_height_mm + 1e-3:
            errors.append(f"Conushoogte ({np.max(self.z_profile):.1f} mm) overschrijdt maximale hoogte ({self.sandbox.max_height_mm:.1f} mm)")

        # 3. Monotonie in straal (r moet naar buiten toenemen)
        dr = np.diff(self.r_profile)
        if np.any(dr < -1e-3):
            errors.append("Conusprofiel bevat omkeringen in radius (geen geldige geometrie)")

        # 4. Overhangcontrole
        if self.sandbox.overhang_check_enabled:
            dz = np.diff(self.z_profile)
            # Hoek t.o.v. verticaal Z-as: theta = arctan(dr / dz)
            # Als dz == 0 (puur horizontaal), overhang = 90 graden
            with np.errstate(divide='ignore', invalid='ignore'):
                angles_rad = np.arctan2(dr, dz) # 0 is verticaal (dr=0), 90 deg is horizontaal (dz=0)
                angles_deg = np.degrees(angles_rad)

            # Alleen controleren op het conuswandgedeelte (flens aan uiteinde kan printbaar zijn als rand)
            # Conuswand is tussen collar en flens
            cone_angles = angles_deg[5:-5]
            max_angle = float(np.max(cone_angles)) if len(cone_angles) > 0 else 0.0
            if max_angle > self.sandbox.max_overhang_angle_deg:
                errors.append(f"Overhanghoek ({max_angle:.1f}°) overschrijdt maximaal toegestane overhanghoek ({self.sandbox.max_overhang_angle_deg:.1f}°)")

        # 5. Keep-out zones
        for i, kz in enumerate(self.sandbox.keep_out_zones):
            # Check of profielpunten in de zone vallen
            in_r = (self.r_profile >= kz.r_min) & (self.r_profile <= kz.r_max)
            in_z = (self.z_profile >= kz.z_min) & (self.z_profile <= kz.z_max)
            if np.any(in_r & in_z):
                errors.append(f"Profiel kruist Keep-out Zone #{i+1} [r:{kz.r_min}-{kz.r_max}, z:{kz.z_min}-{kz.z_max}]")

        return (len(errors) == 0, errors)

    def _calculate_physical_properties(self) -> Tuple[float, float, float]:
        """
        Berekent volume (mm3), conusmassa (g) en structurele stijfheidsindex
        door integratie van conische schaalfrustums.
        """
        # Segmenten integratie: Pappus-Guldinus stelling voor omwentelingslichamen
        # Oppervlakte dS = 2 * pi * r_mid * ds
        # Volume dV = dS * thickness
        dr = np.diff(self.r_profile)
        dz = np.diff(self.z_profile)
        ds = np.sqrt(dr**2 + dz**2)

        r_mid = (self.r_profile[:-1] + self.r_profile[1:]) / 2.0
        t_mid = (self.thickness_profile[:-1] + self.thickness_profile[1:]) / 2.0

        surface_area_segments = 2.0 * np.pi * r_mid * ds
        volume_segments_mm3 = surface_area_segments * t_mid
        total_volume_mm3 = float(np.sum(volume_segments_mm3))

        # Dichtheid in g/cm3 -> omrekenen naar g/mm3: factor 1e-3
        density_g_mm3 = self.material.density_g_cm3 * 1e-3
        mass_g = total_volume_mm3 * density_g_mm3

        # Structurele stijfheidsindex:
        # Hangt af van Young's modulus E, conusdiepte H en conuskromming (oppervlakte-traagheid moment)
        # Biegstijfheid D = E * t^3 / (12*(1-nu^2))
        # Plus conusvormfactor (kromming z t.o.v. vlakke schijf)
        total_depth = float(np.max(self.z_profile) - np.min(self.z_profile))
        depth_factor = 1.0 + (total_depth / (self.sandbox.max_diameter_mm / 2.0)) ** 1.5

        # Gemiddelde schaalbuigstijfheid
        mean_t = float(np.mean(t_mid))
        e_mod = self.material.youngs_modulus_gpa * 1e9 # Pa
        nu = self.material.poisson_ratio
        d_bending = (e_mod * ((mean_t * 1e-3) ** 3)) / (12.0 * (1.0 - nu**2))

        # Stijfheidsindex genormaliseerd (hoger is stijver)
        stiffness_index = float((d_bending * 1e3) * depth_factor)

        return total_volume_mm3, mass_g, stiffness_index

    def generate_mesh(self, angular_segments: int = 64) -> Tuple[np.ndarray, np.ndarray]:
        """
        Genereert een gesloten 3D watervaste mesh (vertices, faces)
        door het profiel (binnenzijde en buitenzijde) 360 graden rond te wentelen.
        """
        num_prof = len(self.r_profile)
        # Bepaal normaalvectoren van profiel om binnen- en buitenwand te construeren
        dr = np.gradient(self.r_profile)
        dz = np.gradient(self.z_profile)
        ds = np.sqrt(dr**2 + dz**2)
        ds[ds == 0] = 1.0

        # Normaalvector n = (-dz, dr)
        nr = -dz / ds
        nz = dr / ds

        # Binnenwand (inner) en Buitenwand (outer)
        half_t = self.thickness_profile / 2.0
        r_outer = self.r_profile + nr * half_t
        z_outer = self.z_profile + nz * half_t

        r_inner = self.r_profile - nr * half_t
        z_inner = self.z_profile - nz * half_t

        # Roteer rond Z-as
        thetas = np.linspace(0, 2 * np.pi, angular_segments, endpoint=False)
        cos_t = np.cos(thetas)
        sin_t = np.sin(thetas)

        # Genereer outer mesh vertices (num_prof x angular_segments)
        outer_verts = []
        for i in range(num_prof):
            for j in range(angular_segments):
                outer_verts.append([r_outer[i] * cos_t[j], r_outer[i] * sin_t[j], z_outer[i]])

        # Genereer inner mesh vertices (num_prof x angular_segments)
        inner_verts = []
        for i in range(num_prof):
            for j in range(angular_segments):
                inner_verts.append([r_inner[i] * cos_t[j], r_inner[i] * sin_t[j], z_inner[i]])

        outer_verts = np.array(outer_verts, dtype=np.float32)
        inner_verts = np.array(inner_verts, dtype=np.float32)

        vertices = np.vstack([outer_verts, inner_verts])
        faces = []

        n_outer = len(outer_verts)

        # Outer surface faces
        for i in range(num_prof - 1):
            for j in range(angular_segments):
                next_j = (j + 1) % angular_segments
                v0 = i * angular_segments + j
                v1 = (i + 1) * angular_segments + j
                v2 = (i + 1) * angular_segments + next_j
                v3 = i * angular_segments + next_j
                faces.append([v0, v1, v2])
                faces.append([v0, v2, v3])

        # Inner surface faces (reversed normal)
        for i in range(num_prof - 1):
            for j in range(angular_segments):
                next_j = (j + 1) % angular_segments
                v0 = n_outer + i * angular_segments + j
                v1 = n_outer + (i + 1) * angular_segments + j
                v2 = n_outer + (i + 1) * angular_segments + next_j
                v3 = n_outer + i * angular_segments + next_j
                faces.append([v0, v2, v1])
                faces.append([v0, v3, v2])

        # Sluit bodem (collar bottom bij i = 0)
        for j in range(angular_segments):
            next_j = (j + 1) % angular_segments
            v_out0 = j
            v_out1 = next_j
            v_in0 = n_outer + j
            v_in1 = n_outer + next_j
            faces.append([v_out0, v_in0, v_in1])
            faces.append([v_out0, v_in1, v_out1])

        # Sluit bovenrand (flange rim bij i = num_prof - 1)
        last_i = num_prof - 1
        for j in range(angular_segments):
            next_j = (j + 1) % angular_segments
            v_out0 = last_i * angular_segments + j
            v_out1 = last_i * angular_segments + next_j
            v_in0 = n_outer + last_i * angular_segments + j
            v_in1 = n_outer + last_i * angular_segments + next_j
            faces.append([v_out0, v_in1, v_in0])
            faces.append([v_out0, v_out1, v_in1])

        return vertices, np.array(faces, dtype=np.int32)

    def export_stl_bytes(self) -> bytes:
        """
        Exporteert conus als binary STL formaat bytes.
        """
        import trimesh
        vertices, faces = self.generate_mesh(angular_segments=48)
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        return mesh.export(file_type='stl')

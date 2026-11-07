import React from 'react';

export default function ProfileCrossSection({ geometryData, sandbox }) {
  if (!geometryData || !geometryData.r_profile) return null;

  const r = geometryData.r_profile;
  const z = geometryData.z_profile;
  const th = geometryData.thickness_profile || [];
  const num = r.length;

  const width = 500;
  const height = 180;
  const padding = { top: 20, right: 30, bottom: 30, left: 45 };

  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const maxR = sandbox.max_diameter_mm / 2.0;
  const maxZ = sandbox.max_height_mm;

  const getX = (rad) => padding.left + (rad / maxR) * plotWidth;
  const getY = (heightVal) => padding.top + plotHeight - (heightVal / maxZ) * plotHeight;

  // Polygoon voor de conusdoorsnede
  let upperPoints = [];
  let lowerPoints = [];

  for (let i = 0; i < num; i++) {
    const t = (th[i] || 1.0) / 2;
    // Bepaal lokale normaal
    const prev_r = i > 0 ? r[i - 1] : r[i];
    const next_r = i < num - 1 ? r[i + 1] : r[i];
    const prev_z = i > 0 ? z[i - 1] : z[i];
    const next_z = i < num - 1 ? z[i + 1] : z[i];
    const dr = (next_r - prev_r) / 2;
    const dz = (next_z - prev_z) / 2;
    const ds = Math.sqrt(dr * dr + dz * dz) || 1;
    const nr = -dz / ds;
    const nz = dr / ds;

    const r_out = r[i] + nr * t;
    const z_out = z[i] + nz * t;
    const r_in = r[i] - nr * t;
    const z_in = z[i] - nz * t;

    upperPoints.push(`${getX(r_out).toFixed(1)},${getY(z_out).toFixed(1)}`);
    lowerPoints.unshift(`${getX(r_in).toFixed(1)},${getY(z_in).toFixed(1)}`);
  }

  const polygonPoints = [...upperPoints, ...lowerPoints].join(' ');

  return (
    <div className="w-full bg-slate-900/80 rounded-xl p-4 border border-slate-700/60 shadow">
      <div className="flex justify-between items-center mb-1">
        <h4 className="text-sm font-semibold text-slate-200">
          2D Conuswand Doorsnede & Wanddikteprofiel
        </h4>
        <span className="text-xs text-slate-400">
          Min: {Math.min(...th).toFixed(2)} mm • Max: {Math.max(...th).toFixed(2)} mm
        </span>
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto text-xs">
        {/* Sandbox grenzen (stippellijn) */}
        <rect
          x={padding.left}
          y={padding.top}
          width={plotWidth}
          height={plotHeight}
          fill="none"
          stroke="#475569"
          strokeDasharray="4 4"
        />

        {/* Keep out zones */}
        {sandbox.keep_out_zones && sandbox.keep_out_zones.map((kz, idx) => {
          const kx = getX(kz.r_min);
          const kw = getX(kz.r_max) - kx;
          const ky = getY(kz.z_max);
          const kh = getY(kz.z_min) - ky;
          return (
            <rect
              key={idx}
              x={kx}
              y={ky}
              width={kw}
              height={kh}
              fill="rgba(239, 68, 68, 0.25)"
              stroke="#ef4444"
              strokeDasharray="2 2"
            />
          );
        })}

        {/* Wanddoorsnede */}
        <polygon points={polygonPoints} fill="#38bdf8" stroke="#0284c7" strokeWidth="1.2" />

        {/* Voice coil montagevlak / collar markering */}
        <line
          x1={getX(sandbox.voice_coil_diameter_mm / 2)}
          y1={getY(0)}
          x2={getX(sandbox.voice_coil_diameter_mm / 2)}
          y2={getY(sandbox.collar_height_mm)}
          stroke="#f59e0b"
          strokeWidth="3"
        />

        {/* As labels */}
        <text x={padding.left - 6} y={padding.top + 10} fill="#94a3b8" textAnchor="end" fontSize="10">
          Z: {maxZ} mm
        </text>
        <text x={padding.left - 6} y={padding.top + plotHeight} fill="#94a3b8" textAnchor="end" fontSize="10">
          Z: 0 mm
        </text>
        <text x={padding.left + plotWidth} y={padding.top + plotHeight + 16} fill="#94a3b8" textAnchor="end" fontSize="10">
          R: {maxR} mm (Ø {sandbox.max_diameter_mm} mm)
        </text>
        <text x={getX(sandbox.voice_coil_diameter_mm / 2)} y={padding.top + plotHeight + 16} fill="#f59e0b" textAnchor="middle" fontSize="10">
          Spoel Ø {sandbox.voice_coil_diameter_mm}
        </text>
      </svg>
      <div className="flex justify-between items-center text-[11px] text-slate-400 mt-1 px-2">
        <span>Radiale afstand R (mm)</span>
        <span className="text-amber-400/90 font-medium">■ Spreekspoel montagekraag (collar)</span>
      </div>
    </div>
  );
}

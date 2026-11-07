import React from 'react';

export default function FrequencyChart({ frequencyResponse, fBreakup }) {
  if (!frequencyResponse || frequencyResponse.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-500 text-sm bg-slate-900/50 rounded-xl border border-slate-800">
        Geen frequentierespons data beschikbaar (voltooi Fase 2 simulatie)
      </div>
    );
  }

  // Bepaal min en max voor schaling
  const minFreq = 20;
  const maxFreq = 20000;
  const minSpl = 50;
  const maxSpl = 105;

  const width = 600;
  const height = 260;
  const padding = { top: 25, right: 30, bottom: 40, left: 45 };

  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  // Logaritmische frequentieschaal
  const getX = (freq) => {
    const logMin = Math.log10(minFreq);
    const logMax = Math.log10(maxFreq);
    const logF = Math.log10(freq);
    return padding.left + ((logF - logMin) / (logMax - logMin)) * plotWidth;
  };

  const getY = (spl) => {
    const clamped = Math.max(minSpl, Math.min(maxSpl, spl));
    return padding.top + plotHeight - ((clamped - minSpl) / (maxSpl - minSpl)) * plotHeight;
  };

  // Construeer SVG pad
  const pathD = frequencyResponse.reduce((acc, pt, idx) => {
    const x = getX(pt.freq);
    const y = getY(pt.spl);
    return `${acc} ${idx === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
  }, '');

  const majorFreqs = [50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000];
  const splTicks = [60, 70, 80, 90, 100];

  const breakupX = fBreakup ? getX(fBreakup) : null;

  return (
    <div className="w-full bg-slate-900/80 rounded-xl p-4 border border-slate-700/60 shadow">
      <div className="flex justify-between items-center mb-2">
        <h4 className="text-sm font-semibold text-slate-200">
          Gesimuleerde Free-Air Frequentierespons (SPL @ 1W/1m)
        </h4>
        {fBreakup && (
          <span className="text-xs bg-amber-500/10 text-amber-400 border border-amber-500/30 px-2 py-0.5 rounded font-mono">
            Breakup: ~{Math.round(fBreakup)} Hz
          </span>
        )}
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto text-xs">
        {/* Rasterlijnen SPL */}
        {splTicks.map((spl) => {
          const y = getY(spl);
          return (
            <g key={spl}>
              <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="#334155" strokeDasharray="3 3" />
              <text x={padding.left - 8} y={y + 4} fill="#94a3b8" textAnchor="end" fontSize="10">
                {spl} dB
              </text>
            </g>
          );
        })}

        {/* Rasterlijnen Frequentie */}
        {majorFreqs.map((freq) => {
          const x = getX(freq);
          return (
            <g key={freq}>
              <line x1={x} y1={padding.top} x2={x} y2={height - padding.bottom} stroke="#1e293b" />
              <text x={x} y={height - padding.bottom + 16} fill="#94a3b8" textAnchor="middle" fontSize="10">
                {freq >= 1000 ? `${freq / 1000}k` : freq}
              </text>
            </g>
          );
        })}

        {/* Breakup indicatielijn */}
        {breakupX && breakupX >= padding.left && breakupX <= width - padding.right && (
          <g>
            <line x1={breakupX} y1={padding.top} x2={breakupX} y2={height - padding.bottom} stroke="#f59e0b" strokeWidth="1.5" strokeDasharray="4 2" />
            <text x={breakupX} y={padding.top - 6} fill="#f59e0b" textAnchor="middle" fontSize="10" fontWeight="bold">
              f_breakup
            </text>
          </g>
        )}

        {/* Frequentiecurve */}
        <path d={pathD} fill="none" stroke="#38bdf8" strokeWidth="2.5" strokeLinecap="round" />
      </svg>
      <div className="flex justify-between items-center text-[11px] text-slate-400 mt-1 px-2">
        <span>Frequentie (Hz)</span>
        <span>Vrije lucht (free-air, 2.83V)</span>
      </div>
    </div>
  );
}

import React, { useState, useEffect, useRef } from 'react';
import {
  Play,
  Square,
  Download,
  Settings,
  Layers,
  Activity,
  CheckCircle,
  AlertTriangle,
  RotateCw,
  Sliders,
  UploadCloud,
  FileCode,
  ShieldCheck,
  ChevronRight,
  Info
} from 'lucide-react';
import ConeViewer3D from './components/ConeViewer3D';
import FrequencyChart from './components/FrequencyChart';
import ProfileCrossSection from './components/ProfileCrossSection';

export default function App() {
  const [activeTab, setActiveTab] = useState('monitor'); // 'setup', 'weights', 'monitor', 'inspect'
  const [loading, setLoading] = useState(false);
  const [isRunning, setIsRunning] = useState(false);

  // Configuratie state
  const [sandbox, setSandbox] = useState({
    max_diameter_mm: 165.0,
    max_height_mm: 45.0,
    voice_coil_diameter_mm: 25.4,
    collar_height_mm: 4.0,
    collar_thickness_mm: 1.2,
    min_wall_thickness_mm: 0.4,
    max_wall_thickness_mm: 2.5,
    overhang_check_enabled: true,
    max_overhang_angle_deg: 65.0,
    keep_out_zones: []
  });

  const [motor, setMotor] = useState({
    name: 'Standard 6.5" Woofer',
    bl: 6.5,
    re: 5.8,
    voice_coil_mass_g: 4.2,
    voice_coil_diameter_mm: 25.4,
    cms_mm_n: 0.65,
    rms_kg_s: 1.2
  });

  const [material, setMaterial] = useState({
    name: 'PLA',
    density_g_cm3: 1.24,
    youngs_modulus_gpa: 3.5,
    poisson_ratio: 0.36,
    loss_factor: 0.04
  });

  const [weights, setWeights] = useState({
    weight_mass: 1.2,
    weight_stiffness: 1.0,
    weight_sensitivity: 1.5,
    weight_target_fs: 1.0,
    target_fs_hz: 45.0,
    weight_linearity: 1.5,
    target_freq_min_hz: 40.0,
    target_freq_max_hz: 5000.0
  });

  const [gaConfig, setGaConfig] = useState({
    total_generations: 40,
    phase1_generations: 15,
    population_size_phase1: 30,
    population_size_phase2: 12,
    mutation_rate: 0.25,
    crossover_rate: 0.7
  });

  // Presets & optimalisatiestatus
  const [presets, setPresets] = useState(null);
  const [status, setStatus] = useState(null);
  const [previewResult, setPreviewResult] = useState(null);
  const [flangeFile, setFlangeFile] = useState(null);
  const [flangeUploadStatus, setFlangeUploadStatus] = useState(null);

  // 3D weergave opties
  const [viewWireframe, setViewWireframe] = useState(false);
  const [viewCutaway, setViewCutaway] = useState(true);

  // Laad presets bij start
  useEffect(() => {
    fetch('/api/presets')
      .then((res) => res.json())
      .then((data) => {
        setPresets(data);
        if (data.default_sandbox) setSandbox(data.default_sandbox);
        if (data.default_weights) setWeights(data.default_weights);
        if (data.default_ga_config) setGaConfig(data.default_ga_config);
      })
      .catch((err) => console.error('Preset error:', err));
  }, []);

  // Polling voor live GA status
  useEffect(() => {
    const interval = setInterval(() => {
      fetch('/api/optimization/status')
        .then((res) => res.json())
        .then((data) => {
          setStatus(data);
          setIsRunning(data.is_running);
          if (data.best) {
            setPreviewResult(data.best);
          }
        })
        .catch((err) => console.error('Status polling error:', err));
    }, 800);
    return () => clearInterval(interval);
  }, []);

  const handleStartOptimization = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/optimization/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox,
          material,
          motor,
          weights,
          ga_config: gaConfig
        })
      });
      if (res.ok) {
        setIsRunning(true);
        setActiveTab('monitor');
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleStopOptimization = async () => {
    try {
      await fetch('/api/optimization/stop', { method: 'POST' });
      setIsRunning(false);
    } catch (err) {
      console.error(err);
    }
  };

  const handleGeneratePreview = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/evaluate-single', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox,
          material,
          motor,
          weights,
          ga_config: gaConfig
        })
      });
      const data = await res.json();
      setPreviewResult({
        generation: 0,
        fitness: 0,
        is_valid: data.is_valid,
        validation_errors: data.validation_errors,
        metrics: data.metrics,
        geometry: data.geometry
      });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleFlangeUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setFlangeFile(file);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch('/api/flange/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        setFlangeUploadStatus(`Geïmporteerd: ${data.info.filename} (Ø: ${data.info.outer_diameter_mm} mm)`);
      } else {
        setFlangeUploadStatus(`Fout: ${data.detail}`);
      }
    } catch (err) {
      setFlangeUploadStatus('Fout bij uploaden STL bestand');
    }
  };

  const handleAddKeepOutZone = () => {
    setSandbox({
      ...sandbox,
      keep_out_zones: [
        ...sandbox.keep_out_zones,
        { r_min: 25.0, r_max: 35.0, z_min: 5.0, z_max: 15.0 }
      ]
    });
  };

  const handleRemoveKeepOutZone = (idx) => {
    const updated = [...sandbox.keep_out_zones];
    updated.splice(idx, 1);
    setSandbox({ ...sandbox, keep_out_zones: updated });
  };

  const currentResult = previewResult || status?.best;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur px-6 py-4 flex flex-wrap justify-between items-center gap-4 sticky top-0 z-50">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-500 flex items-center justify-center shadow-lg shadow-sky-500/20">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              Luidsprekerconus Optimalisatie Studio
              <span className="text-[10px] tracking-widest uppercase px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/30">
                Multi-Fidelity GA
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              Zelflerend optimalisatieprogramma voor 3D-printbare luidsprekerconussen
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-3">
          {isRunning ? (
            <button
              onClick={handleStopOptimization}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg font-medium text-sm transition shadow-lg shadow-red-600/30"
            >
              <Square className="w-4 h-4 fill-white" /> Optimalisatie Stoppen
            </button>
          ) : (
            <button
              onClick={handleStartOptimization}
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white rounded-lg font-medium text-sm transition shadow-lg shadow-sky-500/25 cursor-pointer"
            >
              <Play className="w-4 h-4 fill-white" /> Start Optimalisatie
            </button>
          )}

          <a
            href="/api/export-stl"
            download
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-sm font-medium transition cursor-pointer"
          >
            <Download className="w-4 h-4 text-sky-400" /> Export STL
          </a>
        </div>
      </header>

      {/* Nav Tabs */}
      <nav className="flex px-6 border-b border-slate-800 bg-slate-900/40 text-sm">
        <button
          onClick={() => setActiveTab('monitor')}
          className={`py-3 px-4 border-b-2 font-medium flex items-center gap-2 transition ${
            activeTab === 'monitor'
              ? 'border-sky-500 text-sky-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Activity className="w-4 h-4" /> 3. Genereren & Simuleren (Live)
        </button>
        <button
          onClick={() => setActiveTab('setup')}
          className={`py-3 px-4 border-b-2 font-medium flex items-center gap-2 transition ${
            activeTab === 'setup'
              ? 'border-sky-500 text-sky-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Settings className="w-4 h-4" /> 1. Invoer, Motor & Sandbox
        </button>
        <button
          onClick={() => setActiveTab('weights')}
          className={`py-3 px-4 border-b-2 font-medium flex items-center gap-2 transition ${
            activeTab === 'weights'
              ? 'border-sky-500 text-sky-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sliders className="w-4 h-4" /> 2. Punten & Prioriteiten
        </button>
        <button
          onClick={() => setActiveTab('inspect')}
          className={`py-3 px-4 border-b-2 font-medium flex items-center gap-2 transition ${
            activeTab === 'inspect'
              ? 'border-sky-500 text-sky-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Layers className="w-4 h-4" /> 4. Ontwerp Inspectie & STL
        </button>
      </nav>

      {/* Main Content Area */}
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
        {/* TAB 1 & 2: SETUP & SANDBOX */}
        {activeTab === 'setup' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Sandbox & 3D Printgrenzen */}
            <div className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800 space-y-4">
              <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
                <ShieldCheck className="w-5 h-5 text-sky-400" />
                <h3 className="font-semibold text-slate-100">Sandbox & Harde 3D-Printgrenzen</h3>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Max Conusdiameter (mm)</label>
                  <input
                    type="number"
                    value={sandbox.max_diameter_mm}
                    onChange={(e) => setSandbox({ ...sandbox, max_diameter_mm: parseFloat(e.target.value) || 0 })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Max Conushoogte (mm)</label>
                  <input
                    type="number"
                    value={sandbox.max_height_mm}
                    onChange={(e) => setSandbox({ ...sandbox, max_height_mm: parseFloat(e.target.value) || 0 })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Spreekspoeldiameter (mm)</label>
                  <input
                    type="number"
                    value={sandbox.voice_coil_diameter_mm}
                    onChange={(e) => setSandbox({ ...sandbox, voice_coil_diameter_mm: parseFloat(e.target.value) || 0 })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Montagevlak (Collar) Hoogte (mm)</label>
                  <input
                    type="number"
                    value={sandbox.collar_height_mm}
                    onChange={(e) => setSandbox({ ...sandbox, collar_height_mm: parseFloat(e.target.value) || 0 })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Min. Wanddikte (Harde grens, mm)</label>
                  <input
                    type="number"
                    step="0.05"
                    value={sandbox.min_wall_thickness_mm}
                    onChange={(e) => setSandbox({ ...sandbox, min_wall_thickness_mm: parseFloat(e.target.value) || 0.4 })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white font-mono text-sky-400"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Max Toegestane Overhang (°)</label>
                  <input
                    type="number"
                    value={sandbox.max_overhang_angle_deg}
                    onChange={(e) => setSandbox({ ...sandbox, max_overhang_angle_deg: parseFloat(e.target.value) || 60 })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white"
                  />
                </div>
              </div>

              {/* Overhang switch */}
              <div className="flex items-center justify-between p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                <div>
                  <span className="text-sm font-medium text-slate-200">Overhangcontrole (Harde Afkeur)</span>
                  <p className="text-xs text-slate-400">Wijs conussen met te steile print-overhang direct af</p>
                </div>
                <button
                  onClick={() => setSandbox({ ...sandbox, overhang_check_enabled: !sandbox.overhang_check_enabled })}
                  className={`px-3 py-1 text-xs rounded-full font-bold uppercase transition ${
                    sandbox.overhang_check_enabled
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                      : 'bg-slate-800 text-slate-400 border border-slate-700'
                  }`}
                >
                  {sandbox.overhang_check_enabled ? 'AAN' : 'UIT'}
                </button>
              </div>

              {/* Keep-out Zones */}
              <div className="border-t border-slate-800 pt-3">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Keep-Out Zones (Vermijdingszones)
                  </span>
                  <button
                    onClick={handleAddKeepOutZone}
                    className="text-xs px-2 py-1 bg-slate-800 hover:bg-slate-700 text-sky-400 rounded border border-slate-700"
                  >
                    + Voeg Zone Toe
                  </button>
                </div>
                {sandbox.keep_out_zones.length === 0 ? (
                  <p className="text-xs text-slate-500 italic">Geen keep-out zones ingesteld.</p>
                ) : (
                  <div className="space-y-2">
                    {sandbox.keep_out_zones.map((kz, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs bg-slate-950 p-2 rounded border border-red-500/30">
                        <span className="text-red-400 font-mono">Zone #{i+1}: R:[{kz.r_min}-{kz.r_max}] Z:[{kz.z_min}-{kz.z_max}] mm</span>
                        <button
                          onClick={() => handleRemoveKeepOutZone(i)}
                          className="ml-auto text-red-400 hover:text-red-300 px-1 font-bold"
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Motor & Materiaal specificaties */}
            <div className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <Settings className="w-5 h-5 text-amber-400" />
                  <h3 className="font-semibold text-slate-100">Luidsprekermotor & Materiaal</h3>
                </div>
                {/* Motor Presets */}
                {presets?.motors && (
                  <select
                    onChange={(e) => {
                      if (presets.motors[e.target.value]) {
                        setMotor(presets.motors[e.target.value]);
                      }
                    }}
                    className="bg-slate-950 text-xs border border-slate-700 rounded p-1 text-slate-300"
                  >
                    <option value="">Preset kiezen...</option>
                    <option value="4_inch">4" Midwoofer</option>
                    <option value="6.5_inch">6.5" Woofer</option>
                    <option value="8_inch">8" Sub/Woofer</option>
                  </select>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Krachtfactor Bl (N/A)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={motor.bl}
                    onChange={(e) => setMotor({ ...motor, bl: parseFloat(e.target.value) || 0 })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Gelijkstroomweerstand Re (Ω)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={motor.re}
                    onChange={(e) => setMotor({ ...motor, re: parseFloat(e.target.value) || 0 })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Spreekspoelmassa Mvc (gram)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={motor.voice_coil_mass_g}
                    onChange={(e) => setMotor({ ...motor, voice_coil_mass_g: parseFloat(e.target.value) || 0 })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Compliantie Cms (mm/N)</label>
                  <input
                    type="number"
                    step="0.05"
                    value={motor.cms_mm_n}
                    onChange={(e) => setMotor({ ...motor, cms_mm_n: parseFloat(e.target.value) || 0 })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white"
                  />
                </div>
              </div>

              {/* Materiaalkeuze */}
              <div className="border-t border-slate-800 pt-3">
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-2">
                  3D-Print Filament Materiaal
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {presets?.materials &&
                    Object.keys(presets.materials).map((matName) => (
                      <button
                        key={matName}
                        onClick={() => setMaterial(presets.materials[matName])}
                        className={`p-2 rounded-lg text-xs font-bold border transition ${
                          material.name === matName
                            ? 'bg-sky-500/20 text-sky-400 border-sky-500'
                            : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700'
                        }`}
                      >
                        {matName}
                      </button>
                    ))}
                </div>
                <p className="text-xs text-slate-400 mt-2">
                  Dichtheid: {material.density_g_cm3} g/cm³ • Elasticiteit: {material.youngs_modulus_gpa} GPa
                </p>
              </div>

              {/* Flens Upload STL */}
              <div className="border-t border-slate-800 pt-3">
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-2">
                  Montageflens / Interface STL Upload
                </label>
                <div className="flex items-center gap-3">
                  <label className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700 text-xs font-medium cursor-pointer text-slate-200">
                    <UploadCloud className="w-4 h-4 text-sky-400" />
                    Kies STL Bestand
                    <input type="file" accept=".stl" onChange={handleFlangeUpload} className="hidden" />
                  </label>
                  {flangeUploadStatus && (
                    <span className="text-xs text-sky-400 font-mono truncate">{flangeUploadStatus}</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: WEIGHTS & PRIORITIES */}
        {activeTab === 'weights' && (
          <div className="max-w-3xl mx-auto bg-slate-900/60 p-6 rounded-2xl border border-slate-800 space-y-6">
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
              <Sliders className="w-5 h-5 text-indigo-400" />
              <div>
                <h3 className="font-semibold text-slate-100">Scoreprioriteiten & Akoestische Doelen</h3>
                <p className="text-xs text-slate-400">
                  Stel in hoe zwaar de verschillende fysieke en akoestische criteria meetellen in het genetisch algoritme
                </p>
              </div>
            </div>

            <div className="space-y-4">
              {/* Doel Fs */}
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 flex justify-between items-center">
                <div>
                  <span className="text-sm font-medium text-slate-200">Gewenste resonantiefrequentie (Fs)</span>
                  <p className="text-xs text-slate-400">Het GA probeert de conusmassa hierop af te stemmen</p>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={weights.target_fs_hz}
                    onChange={(e) => setWeights({ ...weights, target_fs_hz: parseFloat(e.target.value) || 45 })}
                    className="w-20 bg-slate-900 border border-slate-700 rounded p-1.5 text-right font-mono text-white text-sm"
                  />
                  <span className="text-xs text-slate-400">Hz</span>
                </div>
              </div>

              {/* Slider Conusgewicht */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-300 font-medium">Licht Conusgewicht (Lagere Massa Mms)</span>
                  <span className="text-sky-400 font-bold">{weights.weight_mass}x</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="3.0"
                  step="0.1"
                  value={weights.weight_mass}
                  onChange={(e) => setWeights({ ...weights, weight_mass: parseFloat(e.target.value) })}
                  className="w-full accent-sky-500 cursor-pointer"
                />
              </div>

              {/* Slider Stijfheid */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-300 font-medium">Mechanische Schaalstijfheid (Vormsterkte)</span>
                  <span className="text-indigo-400 font-bold">{weights.weight_stiffness}x</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="3.0"
                  step="0.1"
                  value={weights.weight_stiffness}
                  onChange={(e) => setWeights({ ...weights, weight_stiffness: parseFloat(e.target.value) })}
                  className="w-full accent-indigo-500 cursor-pointer"
                />
              </div>

              {/* Slider Gevoeligheid */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-300 font-medium">Geluidsdruk & Gevoeligheid (SPL dB @ 1W/1m)</span>
                  <span className="text-emerald-400 font-bold">{weights.weight_sensitivity}x</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="3.0"
                  step="0.1"
                  value={weights.weight_sensitivity}
                  onChange={(e) => setWeights({ ...weights, weight_sensitivity: parseFloat(e.target.value) })}
                  className="w-full accent-emerald-500 cursor-pointer"
                />
              </div>

              {/* Slider Lineariteit */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-300 font-medium">Vlakke Frequentierespons (Minimale Breakup Rimpel)</span>
                  <span className="text-amber-400 font-bold">{weights.weight_linearity}x</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="3.0"
                  step="0.1"
                  value={weights.weight_linearity}
                  onChange={(e) => setWeights({ ...weights, weight_linearity: parseFloat(e.target.value) })}
                  className="w-full accent-amber-500 cursor-pointer"
                />
              </div>
            </div>

            {/* GA Parameters */}
            <div className="border-t border-slate-800 pt-4 grid grid-cols-2 gap-4 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Totaal Generaties (bijv. 40 of 50)</label>
                <input
                  type="number"
                  value={gaConfig.total_generations}
                  onChange={(e) => setGaConfig({ ...gaConfig, total_generations: parseInt(e.target.value) || 30 })}
                  className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-white"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Fase 1 Schifting Generaties (bijv. 15)</label>
                <input
                  type="number"
                  value={gaConfig.phase1_generations}
                  onChange={(e) => setGaConfig({ ...gaConfig, phase1_generations: parseInt(e.target.value) || 10 })}
                  className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-white"
                />
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: MONITOR & LIVE RUN */}
        {activeTab === 'monitor' && (
          <div className="space-y-6">
            {/* Status & Fase Indicatoren */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-slate-900/70 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400 block">Optimalisatie Status</span>
                <span className="text-lg font-bold flex items-center gap-2 mt-1">
                  {isRunning ? (
                    <>
                      <RotateCw className="w-4 h-4 text-sky-400 animate-spin" />
                      <span className="text-sky-400">Actief Genereren</span>
                    </>
                  ) : (
                    <span className="text-slate-400">Gereed / Gepauzeerd</span>
                  )}
                </span>
              </div>

              <div className="bg-slate-900/70 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400 block">Huidige Fase</span>
                <span className="text-lg font-bold text-white mt-1 block">
                  {status?.phase === 1 ? (
                    <span className="text-amber-400">Fase 1: Snelle Schifting</span>
                  ) : (
                    <span className="text-emerald-400">Fase 2: Verfijning</span>
                  )}
                </span>
              </div>

              <div className="bg-slate-900/70 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400 block">Generatie Voortgang</span>
                <span className="text-lg font-bold font-mono text-white mt-1 block">
                  {status?.current_gen || 0} / {status?.total_gen || gaConfig.total_generations}
                </span>
              </div>

              <div className="bg-slate-900/70 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400 block">Beste Fitness Score</span>
                <span className="text-lg font-bold font-mono text-sky-400 mt-1 block">
                  {currentResult?.fitness !== undefined ? currentResult.fitness : '—'}
                </span>
              </div>
            </div>

            {/* 3D Visualisatie & Grafieken Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Linker kolom: 3D Model & 2D Profile */}
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                    <Layers className="w-4 h-4 text-sky-400" /> 3D Conus Model (Interactief)
                  </h3>
                  <div className="flex items-center gap-2 text-xs">
                    <button
                      onClick={() => setViewCutaway(!viewCutaway)}
                      className={`px-2.5 py-1 rounded border transition ${
                        viewCutaway ? 'bg-sky-500/20 text-sky-400 border-sky-500/40' : 'bg-slate-800 text-slate-400 border-slate-700'
                      }`}
                    >
                      Doorsnede (3/4)
                    </button>
                    <button
                      onClick={() => setViewWireframe(!viewWireframe)}
                      className={`px-2.5 py-1 rounded border transition ${
                        viewWireframe ? 'bg-sky-500/20 text-sky-400 border-sky-500/40' : 'bg-slate-800 text-slate-400 border-slate-700'
                      }`}
                    >
                      Wireframe
                    </button>
                    <button
                      onClick={handleGeneratePreview}
                      disabled={isRunning || loading}
                      className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded border border-slate-700"
                    >
                      Preview Nieuw
                    </button>
                  </div>
                </div>

                <ConeViewer3D
                  geometryData={currentResult?.geometry}
                  wireframe={viewWireframe}
                  cutaway={viewCutaway}
                />

                <ProfileCrossSection
                  geometryData={currentResult?.geometry}
                  sandbox={sandbox}
                />
              </div>

              {/* Rechter kolom: Akoestische Respons & Fysische Parameters */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-emerald-400" /> Free-Air Akoestiek & Simulatie
                </h3>

                <FrequencyChart
                  frequencyResponse={currentResult?.metrics?.frequency_response}
                  fBreakup={currentResult?.metrics?.f_breakup_hz}
                />

                {/* Score & Eigenschappen Kaart */}
                <div className="bg-slate-900/80 rounded-xl p-4 border border-slate-800 space-y-3">
                  <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Geverifieerde Conuseigenschappen
                  </h4>

                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
                    <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80">
                      <span className="text-[11px] text-slate-400 block">Conusmassa</span>
                      <span className="font-bold text-white font-mono">
                        {currentResult?.metrics?.cone_mass_g || '—'} g
                      </span>
                    </div>

                    <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80">
                      <span className="text-[11px] text-slate-400 block">Totale Mms</span>
                      <span className="font-bold text-white font-mono">
                        {currentResult?.metrics?.mms_g || '—'} g
                      </span>
                    </div>

                    <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80">
                      <span className="text-[11px] text-slate-400 block">Resonantie Fs</span>
                      <span className="font-bold text-sky-400 font-mono">
                        {currentResult?.metrics?.fs_hz || '—'} Hz
                      </span>
                    </div>

                    <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80">
                      <span className="text-[11px] text-slate-400 block">Gevoeligheid (SPL)</span>
                      <span className="font-bold text-emerald-400 font-mono">
                        {currentResult?.metrics?.sensitivity_db || '—'} dB
                      </span>
                    </div>

                    <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80">
                      <span className="text-[11px] text-slate-400 block">Breakup Mode</span>
                      <span className="font-bold text-amber-400 font-mono">
                        {currentResult?.metrics?.f_breakup_hz ? `${currentResult.metrics.f_breakup_hz} Hz` : '—'}
                      </span>
                    </div>

                    <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80">
                      <span className="text-[11px] text-slate-400 block">Stijfheidsindex</span>
                      <span className="font-bold text-indigo-400 font-mono">
                        {currentResult?.metrics?.stiffness_index || '—'}
                      </span>
                    </div>
                  </div>

                  {/* Printbaarheids Validatie Badges */}
                  <div className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center gap-2">
                    {currentResult?.is_valid ? (
                      <span className="flex items-center gap-1.5 text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2.5 py-1 rounded-full">
                        <CheckCircle className="w-3.5 h-3.5" /> 3D-Printbaar: Voldoet aan alle harde grenzen (wanddikte ≥ 0,4 mm)
                      </span>
                    ) : (
                      <span className="flex items-center gap-1.5 text-xs bg-red-500/10 text-red-400 border border-red-500/30 px-2.5 py-1 rounded-full">
                        <AlertTriangle className="w-3.5 h-3.5" /> Afgekeurd: {currentResult?.validation_errors?.join(', ') || 'Niet printbaar'}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: INSPECT & STL */}
        {activeTab === 'inspect' && (
          <div className="max-w-4xl mx-auto bg-slate-900/60 p-6 rounded-2xl border border-slate-800 space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <FileCode className="w-5 h-5 text-sky-400" />
                  Ontwerp Inspectie & Productie Export
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Download het geoptimaliseerde model direct voor 3D-printen in Bambu Studio, PrusaSlicer of Cura
                </p>
              </div>
              <a
                href="/api/export-stl"
                download
                className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 text-white rounded-xl font-medium text-sm transition shadow-lg shadow-sky-500/25"
              >
                <Download className="w-4 h-4" /> Download STL Bestand
              </a>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Montage & Interface Specificaties
                </h4>
                <ul className="text-xs text-slate-300 space-y-2">
                  <li className="flex justify-between">
                    <span className="text-slate-400">Spreekspoel aansluitkraag (Collar):</span>
                    <span className="font-mono text-white">Ø {sandbox.voice_coil_diameter_mm} mm x {sandbox.collar_height_mm} mm hoog</span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-slate-400">Wanddikte bij collar:</span>
                    <span className="font-mono text-white">{sandbox.collar_thickness_mm} mm</span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-slate-400">Surround montageflens breedte:</span>
                    <span className="font-mono text-white">6.0 mm (horizontaal)</span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-slate-400">Buitenrand diameter:</span>
                    <span className="font-mono text-white">Ø {sandbox.max_diameter_mm} mm</span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-slate-400">Totale bouwhoogte:</span>
                    <span className="font-mono text-white">{sandbox.max_height_mm} mm</span>
                  </li>
                </ul>
              </div>

              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Aanbevolen Slicer Instellingen
                </h4>
                <ul className="text-xs text-slate-300 space-y-2">
                  <li className="flex justify-between">
                    <span className="text-slate-400">Nozzle diameter:</span>
                    <span className="font-mono text-sky-400">0.4 mm (of 0.25 mm voor ultralicht)</span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-slate-400">Laaghoogte:</span>
                    <span className="font-mono text-white">0.12 - 0.16 mm</span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-slate-400">Infill:</span>
                    <span className="font-mono text-white">100% (conuswand is massieve schaal)</span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-slate-400">Wandlijnen:</span>
                    <span className="font-mono text-white">1 tot 3 perimeters</span>
                  </li>
                  <li className="flex justify-between">
                    <span className="text-slate-400">Materiaal:</span>
                    <span className="font-mono text-amber-400">{material.name} ({material.density_g_cm3} g/cm³)</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 px-6 py-4 text-center text-xs text-slate-500">
        Luidsprekerconus Optimalisatie Studio • Multi-Fidelity Genetisch Algoritme • Free-Air Akoestische Simulatie
      </footer>
    </div>
  );
}

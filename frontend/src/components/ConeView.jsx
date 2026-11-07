import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

export default function ConeViewer3D({ geometryData, wireframe = false, cutaway = true }) {
  const mountRef = useRef(null);

  useEffect(() => {
    if (!mountRef.current || !geometryData || !geometryData.r_profile) return;

    const width = mountRef.current.clientWidth;
    const height = mountRef.current.clientHeight || 350;

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0f172a);

    // Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 1, 1000);
    camera.position.set(120, 100, 160);

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;
    mountRef.current.replaceChildren(renderer.domElement);

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0x38bdf8, 1.2);
    dirLight1.position.set(100, 150, 100);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xf59e0b, 0.8);
    dirLight2.position.set(-100, -50, -100);
    scene.add(dirLight2);

    // Grid helper
    const grid = new THREE.GridHelper(200, 20, 0x334155, 0x1e293b);
    grid.position.y = 0;
    scene.add(grid);

    // Generate 3D Mesh from r_profile and z_profile
    const r_profile = geometryData.r_profile;
    const z_profile = geometryData.z_profile;
    const thickness_profile = geometryData.thickness_profile || [];
    const num_prof = r_profile.length;

    // Construeer binnen- en buitenvlak
    const dr = [];
    const dz = [];
    for (let i = 0; i < num_prof; i++) {
      const prev_r = i > 0 ? r_profile[i - 1] : r_profile[i];
      const next_r = i < num_prof - 1 ? r_profile[i + 1] : r_profile[i];
      const prev_z = i > 0 ? z_profile[i - 1] : z_profile[i];
      const next_z = i < num_prof - 1 ? z_profile[i + 1] : z_profile[i];
      dr.push((next_r - prev_r) / 2);
      dz.push((next_z - prev_z) / 2);
    }

    const segments = 48;
    // Als cutaway actief is, draaien we over 270 graden (3/4 conus) voor doorsnede
    const maxTheta = cutaway ? 1.5 * Math.PI : 2 * Math.PI;

    const vertices = [];
    const indices = [];

    // Outer and Inner Rings
    const outerOffset = 0;
    const innerOffset = num_prof * (segments + 1);

    for (let side = 0; side < 2; side++) {
      const sign = side === 0 ? 1 : -1;
      for (let i = 0; i < num_prof; i++) {
        const th = (thickness_profile[i] || 1.0) / 2;
        const ds = Math.sqrt(dr[i] * dr[i] + dz[i] * dz[i]) || 1;
        const nr = -dz[i] / ds;
        const nz = dr[i] / ds;

        const r = r_profile[i] + sign * nr * th;
        const z = z_profile[i] + sign * nz * th;

        for (let j = 0; j <= segments; j++) {
          const theta = (j / segments) * maxTheta;
          const x = r * Math.cos(theta);
          const y = z; // Y is up
          const z_coord = r * Math.sin(theta);
          vertices.push(x, y, z_coord);
        }
      }
    }

    // Indices for outer surface
    const stride = segments + 1;
    for (let i = 0; i < num_prof - 1; i++) {
      for (let j = 0; j < segments; j++) {
        const v0 = i * stride + j;
        const v1 = (i + 1) * stride + j;
        const v2 = (i + 1) * stride + (j + 1);
        const v3 = i * stride + (j + 1);
        indices.push(v0, v1, v2);
        indices.push(v0, v2, v3);
      }
    }

    // Indices for inner surface (reverse normal)
    for (let i = 0; i < num_prof - 1; i++) {
      for (let j = 0; j < segments; j++) {
        const v0 = innerOffset + i * stride + j;
        const v1 = innerOffset + (i + 1) * stride + j;
        const v2 = innerOffset + (i + 1) * stride + (j + 1);
        const v3 = innerOffset + i * stride + (j + 1);
        indices.push(v0, v2, v1);
        indices.push(v0, v3, v2);
      }
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geo.setIndex(indices);
    geo.computeVertexNormals();

    const mat = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      roughness: 0.35,
      metalness: 0.2,
      wireframe: wireframe,
      side: THREE.DoubleSide
    });

    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.y = 0;
    scene.add(mesh);

    // Orbit controls simple mouse drag
    let isDragging = false;
    let prevMouse = { x: 0, y: 0 };
    let rotation = { x: 0.3, y: 0.5 };

    const dom = renderer.domElement;
    const onMouseDown = (e) => {
      isDragging = true;
      prevMouse = { x: e.clientX, y: e.clientY };
    };
    const onMouseMove = (e) => {
      if (!isDragging) return;
      const dx = e.clientX - prevMouse.x;
      const dy = e.clientY - prevMouse.y;
      rotation.y += dx * 0.01;
      rotation.x += dy * 0.01;
      prevMouse = { x: e.clientX, y: e.clientY };
    };
    const onMouseUp = () => { isDragging = false; };
    const onWheel = (e) => {
      camera.position.multiplyScalar(e.deltaY > 0 ? 1.05 : 0.95);
    };

    dom.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    dom.addEventListener('wheel', onWheel);

    let animId;
    const animate = () => {
      animId = requestAnimationFrame(animate);
      if (!isDragging) {
        rotation.y += 0.003; // Gentle auto-rotation
      }
      mesh.rotation.y = rotation.y;
      mesh.rotation.x = rotation.x;
      camera.lookAt(0, geometryData.z_profile[num_prof - 1] / 2 || 20, 0);
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(animId);
      dom.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      dom.removeEventListener('wheel', onWheel);
      renderer.dispose();
    };
  }, [geometryData, wireframe, cutaway]);

  return (
    <div className="relative w-full h-[360px] bg-slate-900 rounded-xl overflow-hidden border border-slate-700/60 shadow-inner">
      <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />
      <div className="absolute top-3 left-3 bg-slate-950/80 backdrop-blur px-2.5 py-1 rounded text-xs text-slate-300 border border-slate-700">
        🖱️ Sleep om te draaien • Scroll voor zoom
      </div>
    </div>
  );
}

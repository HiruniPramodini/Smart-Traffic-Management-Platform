import React, { useState, useEffect, useRef } from 'react';
import './Dashboard.css';

const Dashboard = () => {
  const [simulationState, setSimulationState] = useState(null);
  const [isLive, setIsLive] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [paused, setPaused] = useState(false);
  const [startTime, setStartTime] = useState('08:00');
  const [timePeriod, setTimePeriod] = useState('morning_peak');
  const [weather, setWeather] = useState('clear');
  const [simulationSpeed, setSimulationSpeed] = useState(1);
  const [backendConnected, setBackendConnected] = useState(false);
  const [logs, setLogs] = useState(['[System] Dashboard initialized. Demo mode active.']);

  // Demo mode local states
  const [demoState, setDemoState] = useState({
    elapsed: 0,
    vehicles: [],
    metrics: { spawned: 0, passed: 0, totalWait: 0 },
    junctions: {
      Ranala: { active_phase: 'main_road', in_yellow: false, phase_elapsed: 0, phase_duration: 35, congestion: 0, green_wave: false, gapping: false },
      Malabe: { active_phase: 'main_road', in_yellow: false, phase_elapsed: 0, phase_duration: 35, congestion: 0, green_wave: false, gapping: false },
      Kaduwela: { active_phase: 'main_road', in_yellow: false, phase_elapsed: 0, phase_duration: 45, congestion: 0, green_wave: false, gapping: false },
      Kotikawatta: { active_phase: 'main_road', in_yellow: false, phase_elapsed: 0, phase_duration: 35, congestion: 0, green_wave: false, gapping: false },
      Biyagama: { active_phase: 'main_road', in_yellow: false, phase_elapsed: 0, phase_duration: 35, congestion: 0, green_wave: false, gapping: false }
    }
  });

  const API_BASE = 'http://localhost:8000/api';
  const animationRef = useRef(null);
  const lastTimeRef = useRef(0);

  // Sri Lanka Left-hand coordinates mapping
  const routeCoords = {
    ranala_to_kotikawatta: (p) => ({ x: 0 + p * 800, y: 415, angle: 0 }),
    kotikawatta_to_ranala: (p) => ({ x: 800 - p * 800, y: 385, angle: 180 }),
    malabe_to_biyagama: (p) => ({ x: 385, y: 0 + p * 800, angle: 90 }),
    biyagama_to_malabe: (p) => ({ x: 415, y: 800 - p * 800, angle: 270 }),
    
    ranala_local: (p) => ({ x: 110, y: 300 + p * 200, angle: 90 }),
    kotikawatta_local: (p) => ({ x: 670, y: 300 + p * 200, angle: 90 }),
    malabe_local: (p) => ({ x: 300 + p * 200, y: 110, angle: 0 }),
    biyagama_local: (p) => ({ x: 300 + p * 200, y: 670, angle: 0 })
  };

  const checkpoints = {
    ranala_to_kotikawatta: [
      { name: 'Ranala', check: 120 / 800, stopMin: 90 / 800, stopMax: 115 / 800, phase: 'main_road' },
      { name: 'Kaduwela', check: 400 / 800, stopMin: 370 / 800, stopMax: 395 / 800, phase: 'main_road' },
      { name: 'Kotikawatta', check: 680 / 800, stopMin: 650 / 800, stopMax: 675 / 800, phase: 'main_road' }
    ],
    kotikawatta_to_ranala: [
      { name: 'Kotikawatta', check: (800 - 680) / 800, stopMin: (800 - 710) / 800, stopMax: (800 - 690) / 800, phase: 'main_road' },
      { name: 'Kaduwela', check: (800 - 400) / 800, stopMin: (800 - 430) / 800, stopMax: (800 - 410) / 800, phase: 'main_road' },
      { name: 'Ranala', check: (800 - 120) / 800, stopMin: (800 - 150) / 800, stopMax: (800 - 130) / 800, phase: 'main_road' }
    ],
    malabe_to_biyagama: [
      { name: 'Malabe', check: 120 / 800, stopMin: 90 / 800, stopMax: 115 / 800, phase: 'cross_road' },
      { name: 'Kaduwela', check: 400 / 800, stopMin: 370 / 800, stopMax: 395 / 800, phase: 'cross_road' },
      { name: 'Biyagama', check: 680 / 800, stopMin: 650 / 800, stopMax: 675 / 800, phase: 'cross_road' }
    ],
    biyagama_to_malabe: [
      { name: 'Biyagama', check: (800 - 680) / 800, stopMin: (800 - 710) / 800, stopMax: (800 - 690) / 800, phase: 'cross_road' },
      { name: 'Kaduwela', check: (800 - 400) / 800, stopMin: (800 - 430) / 800, stopMax: (800 - 410) / 800, phase: 'cross_road' },
      { name: 'Malabe', check: (800 - 120) / 800, stopMin: (800 - 150) / 800, stopMax: (800 - 130) / 800, phase: 'cross_road' }
    ],
    ranala_local: [{ name: 'Ranala', check: 0.5, stopMin: 0.35, stopMax: 0.48, phase: 'cross_road' }],
    kotikawatta_local: [{ name: 'Kotikawatta', check: 0.5, stopMin: 0.35, stopMax: 0.48, phase: 'cross_road' }],
    malabe_local: [{ name: 'Malabe', check: 0.5, stopMin: 0.35, stopMax: 0.48, phase: 'main_road' }],
    biyagama_local: [{ name: 'Biyagama', check: 0.5, stopMin: 0.35, stopMax: 0.48, phase: 'main_road' }]
  };

  const getLiveLinkCoords = (link, progress, routeName) => {
    if (link === 'Ranala_source') return { x: 0 + 120 * progress, y: 415, angle: 0 };
    if (link === 'Ranala_to_Kaduwela') return { x: 120 + 280 * progress, y: 415, angle: 0 };
    if (link === 'Kaduwela_to_Kotikawatta') return { x: 400 + 280 * progress, y: 415, angle: 0 };
    if (link === 'Kotikawatta_exit') return { x: 680 + 120 * progress, y: 415, angle: 0 };
    
    if (link === 'Kotikawatta_source') return { x: 800 - 120 * progress, y: 385, angle: 180 };
    if (link === 'Kotikawatta_to_Kaduwela') return { x: 680 - 280 * progress, y: 385, angle: 180 };
    if (link === 'Kaduwela_to_Ranala') return { x: 400 - 280 * progress, y: 385, angle: 180 };
    if (link === 'Ranala_exit') return { x: 120 - 120 * progress, y: 385, angle: 180 };
    
    if (link === 'Malabe_source') return { x: 385, y: 0 + 120 * progress, angle: 90 };
    if (link === 'Malabe_to_Kaduwela') return { x: 385, y: 120 + 280 * progress, angle: 90 };
    if (link === 'Kaduwela_to_Biyagama') return { x: 385, y: 400 + 280 * progress, angle: 90 };
    if (link === 'Biyagama_exit') return { x: 385, y: 680 + 120 * progress, angle: 90 };
    
    if (link === 'Biyagama_source') return { x: 415, y: 800 - 120 * progress, angle: 270 };
    if (link === 'Biyagama_to_Kaduwela') return { x: 415, y: 680 - 280 * progress, angle: 270 };
    if (link === 'Kaduwela_to_Malabe') return { x: 415, y: 400 - 280 * progress, angle: 270 };
    if (link === 'Malabe_exit') return { x: 415, y: 120 - 120 * progress, angle: 270 };
    
    if (link === 'Cross_source_Ranala') return { x: 110, y: 300 + 100 * progress, angle: 90 };
    if (link === 'Cross_source_Kotikawatta') return { x: 670, y: 300 + 100 * progress, angle: 90 };
    if (link === 'Cross_source_Malabe') return { x: 300 + 100 * progress, y: 110, angle: 0 };
    if (link === 'Cross_source_Biyagama') return { x: 300 + 100 * progress, y: 670, angle: 0 };
    
    if (link === 'Cross_exit') {
      if (routeName === 'ranala_local') return { x: 110, y: 400 + 100 * progress, angle: 90 };
      if (routeName === 'kotikawatta_local') return { x: 670, y: 400 + 100 * progress, angle: 90 };
      if (routeName === 'malabe_local') return { x: 400 + 100 * progress, y: 110, angle: 0 };
      if (routeName === 'biyagama_local') return { x: 400 + 100 * progress, y: 670, angle: 0 };
    }

    if (link === 'Ranala') return { x: 120, y: 400, angle: 0 };
    if (link === 'Malabe') return { x: 400, y: 120, angle: 90 };
    if (link === 'Kotikawatta') return { x: 680, y: 400, angle: 180 };
    if (link === 'Biyagama') return { x: 400, y: 680, angle: 270 };
    
    return { x: 400, y: 400, angle: 0 };
  };

  const addLog = (text) => {
    const time = new Date().toLocaleTimeString();
    setLogs(prev => [...prev.slice(-30), `[${time}] ${text}`]);
  };

  // Test live connection
  const checkConnection = async () => {
    try {
      const res = await fetch(`${API_BASE}/`);
      if (res.ok) {
        setBackendConnected(true);
        if (isLive) addLog('Connected to FastAPI XGBoost Agent server.');
      }
    } catch {
      setBackendConnected(false);
      if (isLive) {
        setIsLive(false);
        addLog('FastAPI server is offline. Switched back to Demo Mode.');
      }
    }
  };

  useEffect(() => {
    checkConnection();
    const interval = setInterval(checkConnection, 5000);
    return () => clearInterval(interval);
  }, [isLive]);

  // Start simulation API trigger
  const handleStartSimulation = async () => {
    if (isLive) {
      try {
        await fetch(`${API_BASE}/simulation/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            start_time: startTime,
            time_period: timePeriod,
            weather: weather
          })
        });
        addLog(`FastAPI Simulation started: Weather=${weather}, Period=${timePeriod}`);
      } catch {
        addLog('Failed to connect to FastAPI to start simulation.');
      }
    } else {
      addLog(`Demo Simulation started: Weather=${weather}, Period=${timePeriod}`);
    }
    setIsRunning(true);
    setPaused(false);
  };

  // Step simulation API call (Live mode)
  const handleStep = async () => {
    try {
      const res = await fetch(`${API_BASE}/simulation/step`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ steps: simulationSpeed })
      });
      const data = await res.json();
      setSimulationState(data);
      
      // Update logs from backend agent messages
      if (data.coordination_logs) {
        data.coordination_logs.forEach(log => {
          setLogs(prev => {
            if (!prev.includes(log)) {
              return [...prev, log];
            }
            return prev;
          });
        });
      }
    } catch {
      addLog('Lost connection to backend simulation.');
      setIsRunning(false);
    }
  };

  // Local demo step computation
  const runDemoStep = (dt) => {
    setDemoState(prev => {
      const updated = { ...prev };
      updated.elapsed += dt;

      // 1. Spawning
      const spawnRates = { morning_peak: 2.0, evening_peak: 1.7, off_peak: 1.0, night: 0.3 };
      const rate = spawnRates[timePeriod] || 1.0;
      const weatherMod = weather === 'heavy_rain' ? 0.7 : (weather === 'light_rain' ? 0.85 : 1.0);
      
      if (Math.random() < 0.05 * rate * weatherMod) {
        updated.metrics.spawned++;
        const routes = Object.keys(routeCoords);
        const route = routes[Math.floor(Math.random() * routes.length)];
        
        let speed = 0.06 + Math.random() * 0.04;
        if (weather === 'heavy_rain') speed *= 0.65;
        else if (weather === 'light_rain') speed *= 0.85;

        updated.vehicles.push({
          id: `V${updated.metrics.spawned}`,
          route,
          progress: 0.0,
          speed,
          wait: 0.0,
          color: ['#3b82f6', '#10b981', '#fb923c', '#f472b6', '#a78bfa'][Math.floor(Math.random() * 5)],
          status: 'moving'
        });
      }

      // 2. Light phases
      Object.keys(updated.junctions).forEach(jname => {
        const j = { ...updated.junctions[jname] };
        j.phase_elapsed += dt;

        let activeLimit = j.phase_duration;
        if (j.in_yellow) activeLimit = 3.0;

        if (j.phase_elapsed >= activeLimit) {
          j.phase_elapsed = 0;
          if (j.in_yellow) {
            j.in_yellow = false;
            j.active_phase = j.active_phase === 'main_road' ? 'cross_road' : 'main_road';
            
            // Queue size calculations
            const waiting = updated.vehicles.filter(v => v.status === 'waiting' && checkpoints[v.route]?.some(cp => cp.name === jname)).length;
            j.congestion = waiting > 6 ? 2 : (waiting > 3 ? 1 : 0);
            j.phase_duration = j.congestion === 2 ? 55 : (j.congestion === 1 ? 42 : 30);

            if (j.green_wave) {
              j.phase_duration += 15;
              j.green_wave = false;
              addLog(`[${jname}] GREEN WAVE: priority green override +15s.`);
            }
            if (j.gapping) {
              j.phase_duration = Math.max(20, j.phase_duration - 10);
              j.gapping = false;
              addLog(`[${jname}] PLATOON GAPPING: flow metered -10s.`);
            }
          } else {
            j.in_yellow = true;
            
            // releases downstream green wave platoons
            if (jname === 'Kaduwela') {
              if (j.active_phase === 'main_road') {
                updated.junctions.Kotikawatta = { ...updated.junctions.Kotikawatta, green_wave: true };
                updated.junctions.Ranala = { ...updated.junctions.Ranala, green_wave: true };
                addLog('[Kaduwela → Kotikawatta] Platoon released Eastbound. Green Wave triggered.');
              } else {
                updated.junctions.Malabe = { ...updated.junctions.Malabe, green_wave: true };
                updated.junctions.Biyagama = { ...updated.junctions.Biyagama, green_wave: true };
                addLog('[Kaduwela → Malabe] Platoon released Northbound. Green Wave triggered.');
              }
            }

            // Gapping feedback alerts
            const kotiWaiting = updated.vehicles.filter(v => v.status === 'waiting' && checkpoints[v.route]?.some(cp => cp.name === 'Kotikawatta')).length;
            if (kotiWaiting > 5) {
              updated.junctions.Kaduwela = { ...updated.junctions.Kaduwela, gapping: true };
              addLog('[Kotikawatta → Kaduwela] Downstream congestion HIGH. Requesting Platoon Gapping.');
            }
          }
        }
        updated.junctions[jname] = j;
      });

      // 3. Move vehicles
      updated.vehicles = updated.vehicles.map(v => {
        const cps = checkpoints[v.route] || [];
        let canMove = true;

        for (let cp of cps) {
          if (v.progress >= cp.stopMin && v.progress <= cp.stopMax) {
            const j = updated.junctions[cp.name];
            const isGreen = j.active_phase === cp.phase && !j.in_yellow;
            if (!isGreen) {
              canMove = false;
              break;
            }
          }
        }

        if (canMove) {
          return {
            ...v,
            progress: v.progress + v.speed * dt,
            status: 'moving'
          };
        } else {
          return {
            ...v,
            wait: v.wait + dt,
            status: 'waiting'
          };
        }
      });

      // Cleared checking
      const cleared = updated.vehicles.filter(v => v.progress >= 1.0);
      updated.metrics.passed += cleared.length;
      cleared.forEach(v => {
        updated.metrics.totalWait += v.wait;
      });
      updated.vehicles = updated.vehicles.filter(v => v.progress < 1.0);

      return updated;
    });
  };

  // Main tick loop
  useEffect(() => {
    if (!isRunning || paused) return;

    if (isLive) {
      const interval = setInterval(() => {
        handleStep();
      }, 1000);
      return () => clearInterval(interval);
    } else {
      const loop = (timestamp) => {
        if (!lastTimeRef.current) lastTimeRef.current = timestamp;
        const dt = Math.min(0.03, (timestamp - lastTimeRef.current) / 1000) * simulationSpeed;
        lastTimeRef.current = timestamp;

        runDemoStep(dt);
        animationRef.current = requestAnimationFrame(loop);
      };
      animationRef.current = requestAnimationFrame(loop);
      return () => cancelAnimationFrame(animationRef.current);
    }
  }, [isRunning, paused, isLive, simulationSpeed, weather, timePeriod]);

  const resetSimulation = () => {
    setIsRunning(false);
    setPaused(false);
    setSimulationState(null);
    setLogs(['[System] Simulation reset.']);
    setDemoState({
      elapsed: 0,
      vehicles: [],
      metrics: { spawned: 0, passed: 0, totalWait: 0 },
      junctions: {
        Ranala: { active_phase: 'main_road', in_yellow: false, phase_elapsed: 0, phase_duration: 35, congestion: 0, green_wave: false, gapping: false },
        Malabe: { active_phase: 'main_road', in_yellow: false, phase_elapsed: 0, phase_duration: 35, congestion: 0, green_wave: false, gapping: false },
        Kaduwela: { active_phase: 'main_road', in_yellow: false, phase_elapsed: 0, phase_duration: 45, congestion: 0, green_wave: false, gapping: false },
        Kotikawatta: { active_phase: 'main_road', in_yellow: false, phase_elapsed: 0, phase_duration: 35, congestion: 0, green_wave: false, gapping: false },
        Biyagama: { active_phase: 'main_road', in_yellow: false, phase_elapsed: 0, phase_duration: 35, congestion: 0, green_wave: false, gapping: false }
      }
    });

    if (isLive) {
      fetch(`${API_BASE}/simulation/reset`, { method: 'POST' }).catch(() => {});
    }
  };

  // Compile layout parameters
  const currentJunctions = isLive && simulationState?.junctions ? 
    Object.keys(simulationState.junctions).reduce((acc, name) => {
      const j = simulationState.junctions[name];
      acc[name] = {
        name,
        congestion: j.congestion_level,
        congestion_name: j.congestion_name,
        main_color: j.main_color,
        cross_color: j.cross_color,
        remaining: j.remaining,
        green_wave: j.green_wave_active,
        gapping: j.gapping_active
      };
      return acc;
    }, {}) : 
    Object.keys(demoState.junctions).reduce((acc, name) => {
      const j = demoState.junctions[name];
      const isMain = j.active_phase === 'main_road';
      acc[name] = {
        name,
        congestion: j.congestion,
        congestion_name: ['LOW', 'MEDIUM', 'HIGH'][j.congestion],
        main_color: isMain ? (j.in_yellow ? 'YELLOW' : 'GREEN') : 'RED',
        cross_color: isMain ? 'RED' : (j.in_yellow ? 'YELLOW' : 'GREEN'),
        remaining: Math.max(0, Math.round((j.in_yellow ? 3.0 : j.phase_duration) - j.phase_elapsed)),
        green_wave: j.green_wave,
        gapping: j.gapping
      };
      return acc;
    }, {});

  const currentVehicles = isLive && simulationState?.vehicles ?
    simulationState.vehicles.map(v => ({
      id: v.id,
      color: v.color,
      status: v.status,
      ...getLiveLinkCoords(v.link, v.progress_percent / 100, v.route)
    })) :
    demoState.vehicles.map(v => ({
      id: v.id,
      color: v.color,
      status: v.status,
      ...routeCoords[v.route](v.progress)
    }));

  const metrics = isLive && simulationState?.metrics ? 
    simulationState.metrics : 
    {
      spawned: demoState.metrics.spawned,
      passed: demoState.metrics.passed,
      average_wait: demoState.metrics.passed ? demoState.metrics.totalWait / demoState.metrics.passed : 0
    };

  return (
    <div className="dashboard dark-theme" style={{ background: '#090d1a', color: '#f3f4f6', minHeight: '100vh', padding: '24px' }}>
      <header style={{ border: '1px solid rgba(255,255,255,0.08)', padding: '20px', borderRadius: '16px', background: 'rgba(17,24,39,0.75)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 800, background: 'linear-gradient(to right, #10b981, #3b82f6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', margin: 0 }}>🚦 Smart Traffic Corridor Studio</h1>
          <p style={{ margin: '4px 0 0', color: '#9ca3af', fontSize: '0.9rem' }}>Dynamic 5-Junction Coordinated Green Wave & XGBoost AI Coordination</p>
        </div>
        
        {/* Mode switcher */}
        <div style={{ display: 'flex', background: 'rgba(31, 41, 55, 0.6)', padding: '4px', borderRadius: '99px', border: '1px solid rgba(255,255,255,0.08)' }}>
          <button 
            className={`btn-mode ${!isLive ? 'active' : ''}`}
            style={{ border: 0, padding: '6px 16px', borderRadius: '99px', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer', background: !isLive ? '#3b82f6' : 'transparent', color: !isLive ? '#fff' : '#9ca3af' }}
            onClick={() => { setIsLive(false); resetSimulation(); }}
          >
            Demo (Browser)
          </button>
          <button 
            className={`btn-mode ${isLive ? 'active' : ''}`}
            style={{ border: 0, padding: '6px 16px', borderRadius: '99px', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer', background: isLive ? '#3b82f6' : 'transparent', color: isLive ? '#fff' : '#9ca3af' }}
            onClick={() => { 
              setIsLive(true); 
              resetSimulation();
              if (!backendConnected) addLog('Attempting to connect to FastAPI backend...');
            }}
          >
            Live (XGBoost)
          </button>
        </div>
      </header>

      {/* Control panel and grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '20px' }}>
        
        {/* Controls row */}
        <section style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', alignItems: 'center', background: 'rgba(17,24,39,0.75)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '16px' }}>
          <button className="btn btn-primary" style={{ padding: '10px 20px', borderRadius: '99px', fontWeight: 700, border: 0, cursor: 'pointer', background: 'linear-gradient(135deg, #10b981, #059669)', color: '#fff' }} onClick={handleStartSimulation} disabled={isRunning}>▶ Start</button>
          <button className="btn btn-secondary" style={{ padding: '10px 20px', borderRadius: '99px', fontWeight: 700, border: 0, cursor: 'pointer', background: 'rgba(55,65,81,0.8)', color: '#fff' }} onClick={() => setPaused(!paused)}>{paused ? '▶ Resume' : '⏸ Pause'}</button>
          <button className="btn btn-danger" style={{ padding: '10px 20px', borderRadius: '99px', fontWeight: 700, border: 0, cursor: 'pointer', background: 'linear-gradient(135deg, #ef4444, #dc2626)', color: '#fff' }} onClick={resetSimulation}>⟳ Reset</button>

          <div className="control-group" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#9ca3af', textTransform: 'uppercase' }}>Time Period</label>
            <select style={{ background: '#1f2937', color: '#fff', border: '1px solid rgba(255,255,255,0.1)', padding: '6px 12px', borderRadius: '8px' }} value={timePeriod} onChange={(e) => setTimePeriod(e.target.value)} disabled={isRunning}>
              <option value="morning_peak">Morning Peak</option>
              <option value="evening_peak">Evening Peak</option>
              <option value="off_peak">Off Peak</option>
              <option value="night">Night</option>
            </select>
          </div>

          <div className="control-group" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#9ca3af', textTransform: 'uppercase' }}>Weather</label>
            <select style={{ background: '#1f2937', color: '#fff', border: '1px solid rgba(255,255,255,0.1)', padding: '6px 12px', borderRadius: '8px' }} value={weather} onChange={(e) => setWeather(e.target.value)} disabled={isRunning}>
              <option value="clear">Sunny / Clear</option>
              <option value="overcast">Overcast</option>
              <option value="foggy">Foggy</option>
              <option value="light_rain">Light Monsoon Rain</option>
              <option value="heavy_rain">Heavy Monsoon storm</option>
            </select>
          </div>

          <div className="control-group" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#9ca3af', textTransform: 'uppercase' }}>Sim Speed</label>
            <div style={{ display: 'flex', alignState: 'center', gap: '8px' }}>
              <input type="range" min="1" max="10" value={simulationSpeed} onChange={(e) => setSimulationSpeed(parseInt(e.target.value))} />
              <span style={{ fontSize: '0.85rem', fontWeight: 700 }}>{simulationSpeed}x</span>
            </div>
          </div>

          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', fontWeight: 600, color: isLive ? (backendConnected ? '#10b981' : '#ef4444') : '#10b981' }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'currentColor' }}></div>
            <span>{isLive ? (backendConnected ? 'Python Live Active' : 'Python Server Offline') : 'Local Demo Active'}</span>
          </div>
        </section>

        {/* Network and statistics layouts */}
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '20px' }}>
          
          {/* Canvas block */}
          <div style={{ background: 'rgba(17,24,39,0.75)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '16px', position: 'relative' }}>
            <div style={{ position: 'relative', width: '100%', aspectRatio: '1/1', background: '#020617', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)', overflow: 'hidden' }}>
              
              {/* Roads drawing */}
              <div style={{ position: 'absolute', left: 0, right: 0, top: '370px', height: '60px', background: '#1e293b', borderTop: '1px solid rgba(255,255,255,0.1)', borderBottom: '1px solid rgba(255,255,255,0.1)' }}></div>
              <div style={{ position: 'absolute', top: 0, bottom: 0, left: '370px', width: '60px', background: '#1e293b', borderLeft: '1px solid rgba(255,255,255,0.1)', borderRight: '1px solid rgba(255,255,255,0.1)' }}></div>
              <div style={{ position: 'absolute', left: '110px', top: '300px', bottom: '500px', width: '20px', background: '#1e293b' }}></div>
              <div style={{ position: 'absolute', left: '670px', top: '300px', bottom: '500px', width: '20px', background: '#1e293b' }}></div>
              <div style={{ position: 'absolute', top: '110px', left: '300px', right: '500px', height: '20px', background: '#1e293b' }}></div>
              <div style={{ position: 'absolute', top: '670px', left: '300px', right: '500px', height: '20px', background: '#1e293b' }}></div>

              {/* Vehicles layer */}
              <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 12 }}>
                {currentVehicles.map(v => (
                  <div 
                    key={v.id} 
                    className={`vehicle ${v.status === 'waiting' ? 'waiting' : ''}`}
                    style={{
                      position: 'absolute',
                      left: `${v.x}px`,
                      top: `${v.y}px`,
                      transform: `translate(-50%, -50%) rotate(${v.angle}deg)`,
                      width: '16px',
                      height: '10px',
                      borderRadius: '3px',
                      background: v.color || '#3b82f6',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '0.5rem',
                      fontWeight: 800,
                      color: '#000',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.5)',
                      border: v.status === 'waiting' ? '1px solid rgba(239, 68, 68, 0.8)' : '0'
                    }}
                  >
                    {v.id.replace(/\D/g, '')}
                  </div>
                ))}
              </div>

              {/* Junction details overlay */}
              {Object.keys(currentJunctions).map(name => {
                const j = currentJunctions[name];
                
                // Coordinates
                const pos = {
                  Ranala: { left: '120px', top: '400px' },
                  Kotikawatta: { left: '680px', top: '400px' },
                  Malabe: { left: '400px', top: '120px' },
                  Biyagama: { left: '400px', top: '680px' },
                  Kaduwela: { left: '400px', top: '400px' }
                }[name];

                const colorLevel = j.congestion === 2 ? '#ef4444' : (j.congestion === 1 ? '#f59e0b' : '#10b981');

                return (
                  <div 
                    key={name}
                    style={{
                      position: 'absolute',
                      left: pos.left,
                      top: pos.top,
                      transform: 'translate(-50%, -50%)',
                      width: '90px',
                      height: '90px',
                      borderRadius: '12px',
                      background: 'rgba(15, 23, 42, 0.9)',
                      border: '1px solid rgba(255,255,255,0.15)',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      zIndex: 15,
                      boxShadow: '0 4px 15px rgba(0,0,0,0.5)'
                    }}
                  >
                    <strong style={{ fontSize: '0.72rem', letterSpacing: '0.05em', color: '#fff', textTransform: 'uppercase' }}>{name}</strong>
                    <span style={{ fontSize: '0.58rem', fontWeight: 800, padding: '1px 6px', borderRadius: '99px', marginTop: '4px', background: colorLevel, color: '#fff' }}>{j.congestion_name}</span>
                    
                    {/* Small signal lights dots */}
                    <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
                      <div 
                        style={{ 
                          width: '8px', 
                          height: '8px', 
                          borderRadius: '50%', 
                          background: j.main_color === 'GREEN' ? '#10b981' : (j.main_color === 'YELLOW' ? '#f59e0b' : '#ef4444'),
                          boxShadow: `0 0 8px ${j.main_color === 'GREEN' ? '#10b981' : (j.main_color === 'YELLOW' ? '#f59e0b' : '#ef4444')}`
                        }}
                        title="Main corridor"
                      ></div>
                      <div 
                        style={{ 
                          width: '8px', 
                          height: '8px', 
                          borderRadius: '50%', 
                          background: j.cross_color === 'GREEN' ? '#10b981' : (j.cross_color === 'YELLOW' ? '#f59e0b' : '#ef4444'),
                          boxShadow: `0 0 8px ${j.cross_color === 'GREEN' ? '#10b981' : (j.cross_color === 'YELLOW' ? '#f59e0b' : '#ef4444')}`
                        }}
                        title="Cross corridor"
                      ></div>
                    </div>
                  </div>
                );
              })}

            </div>
          </div>

          {/* Stats and console logs column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            {/* Stats row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div style={{ background: 'rgba(31, 41, 55, 0.4)', padding: '14px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', textAlign: 'center' }}>
                <div style={{ fontSize: '0.75rem', color: '#9ca3af', fontWeight: 600, textTransform: 'uppercase', marginBottom: '6px' }}>Spawned</div>
                <div style={{ fontSize: '1.6rem', fontWeight: 800 }}>{metrics.spawned}</div>
              </div>
              <div style={{ background: 'rgba(31, 41, 55, 0.4)', padding: '14px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', textAlign: 'center' }}>
                <div style={{ fontSize: '0.75rem', color: '#9ca3af', fontWeight: 600, textTransform: 'uppercase', marginBottom: '6px' }}>Passed</div>
                <div style={{ fontSize: '1.6rem', fontWeight: 800 }}>{metrics.passed}</div>
              </div>
              <div style={{ gridColumn: 'span 2', background: 'rgba(31, 41, 55, 0.4)', padding: '14px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', textAlign: 'center' }}>
                <div style={{ fontSize: '0.75rem', color: '#9ca3af', fontWeight: 600, textTransform: 'uppercase', marginBottom: '6px' }}>Average Delay</div>
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#3b82f6' }}>{metrics.average_wait.toFixed(1)}s</div>
              </div>
            </div>

            {/* Junctions list summary */}
            <div style={{ background: 'rgba(17,24,39,0.75)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '16px' }}>
              <h3 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#3b82f6', textTransform: 'uppercase', letterSpacing: '0.05em', margin: '0 0 10px 0' }}>Junction States Summary</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {Object.keys(currentJunctions).map(name => {
                  const j = currentJunctions[name];
                  return (
                    <div 
                      key={name} 
                      style={{ 
                        display: 'grid', 
                        gridTemplateColumns: '1.2fr 1fr 1fr 1fr', 
                        fontSize: '0.8rem', 
                        padding: '8px 12px', 
                        background: 'rgba(255,255,255,0.03)', 
                        border: '1px solid rgba(255,255,255,0.05)', 
                        borderRadius: '8px',
                        alignItems: 'center'
                      }}
                    >
                      <span style={{ fontWeight: 700 }}>{name}</span>
                      <span style={{ color: '#9ca3af' }}>{j.main_color === 'GREEN' ? 'Main Green' : (j.cross_color === 'GREEN' ? 'Cross Green' : 'Yellow')}</span>
                      <span style={{ fontWeight: 600, color: j.congestion === 2 ? '#ef4444' : (j.congestion === 1 ? '#f59e0b' : '#10b981') }}>{j.congestion_name}</span>
                      <span style={{ textAlign: 'right', fontWeight: 700 }}>{j.remaining}s</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Console logs */}
            <div style={{ background: 'rgba(17,24,39,0.75)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '16px', flexGrow: 1, display: 'flex', flexDirection: 'column', minHeight: '220px' }}>
              <h3 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#3b82f6', textTransform: 'uppercase', letterSpacing: '0.05em', margin: '0 0 10px 0' }}>⚡ Coordination Network Logs</h3>
              <div 
                style={{ 
                  background: 'rgba(11,15,26,0.9)', 
                  border: '1px solid rgba(255,255,255,0.05)', 
                  borderRadius: '10px', 
                  padding: '10px', 
                  flexGrow: 1, 
                  overflowY: 'auto', 
                  fontFamily: 'monospace', 
                  fontSize: '0.75rem', 
                  display: 'flex', 
                  flexDirection: 'column', 
                  gap: '6px', 
                  color: '#38bdf8' 
                }}
              >
                {logs.map((log, idx) => {
                  const isWarning = log.includes('warning') || log.includes('Gapping');
                  const isGreen = log.includes('released') || log.includes('triggered') || log.includes('GREEN');
                  return (
                    <div 
                      key={idx}
                      style={{
                        padding: '4px 6px',
                        borderRadius: '4px',
                        background: 'rgba(255,255,255,0.02)',
                        borderLeft: `2px solid ${isWarning ? '#f59e0b' : (isGreen ? '#10b981' : '#3b82f6')}`,
                        color: isWarning ? '#f59e0b' : (isGreen ? '#10b981' : '#38bdf8')
                      }}
                    >
                      {log}
                    </div>
                  );
                })}
              </div>
            </div>

          </div>

        </div>

      </div>
    </div>
  );
};

export default Dashboard;

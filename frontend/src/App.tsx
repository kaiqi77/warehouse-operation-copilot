import { Activity, AlertTriangle, Bot, CheckCircle2, Database, Gauge, Network, Play, ShieldCheck } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

type WarehouseSnapshot = {
  orders: Array<{ hour: string; inbound: number; outbound: number; priority: number }>;
  inventory: Array<{ sku: string; on_hand: number; safety_stock: number; daily_demand: number; zone: string }>;
  equipment: Array<{ id: string; type: string; status: string; throughput_per_hour: number; target_throughput: number; queue: number; risk: string }>;
  labor: { planned_heads: number; available_heads: number; pick_rate_per_head: number };
  sla: { target_ship_before_hour: string; target_completion_rate: number };
};

type AgentResponse = {
  task_id: string;
  answer: string;
  recommendations: string[];
  risks: string[];
  next_actions: Array<Record<string, unknown>>;
  steps: Array<{ name: string; thought: string; action: string; observation: Record<string, unknown> }>;
  metrics: Record<string, number>;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

function App() {
  const [snapshot, setSnapshot] = useState<WarehouseSnapshot | null>(null);
  const [question, setQuestion] = useState('Will today\'s outbound peak create shipment delays? Diagnose inventory and equipment risks, then provide a wave planning recommendation.');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentResponse | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch(`${API_BASE}/api/dashboard`)
      .then((response) => response.json())
      .then(setSnapshot)
      .catch(() => setError('Unable to connect to the backend. Please confirm FastAPI is running.'));
  }, []);

  const kpis = useMemo(() => {
    if (!snapshot) return [];
    const totalOutbound = snapshot.orders.reduce((sum, item) => sum + item.outbound, 0);
    const peak = snapshot.orders.reduce((max, item) => (item.outbound > max.outbound ? item : max), snapshot.orders[0]);
    const lowStock = snapshot.inventory.filter((item) => item.on_hand < item.safety_stock).length;
    const degraded = snapshot.equipment.filter((item) => item.status !== 'running').length;
    return [
      { label: 'Today\'s Outbound', value: totalOutbound.toLocaleString(), icon: Activity, tone: 'blue' },
      { label: 'Peak Hour', value: `${peak.hour} / ${peak.outbound}`, icon: Gauge, tone: 'purple' },
      { label: 'Low-Stock SKUs', value: lowStock.toString(), icon: AlertTriangle, tone: 'amber' },
      { label: 'Exception Equipment', value: degraded.toString(), icon: Network, tone: 'red' }
    ];
  }, [snapshot]);

  async function runAgent() {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_BASE}/api/agent/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, user_id: 'shift-lead', urgency: 'high' })
      });
      if (!response.ok) throw new Error('agent failed');
      setResult(await response.json());
    } catch {
      setError('Agent execution failed. Please check the backend service and dependencies.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell">
      <section className="hero">
        <div>
          <div className="eyebrow"><Bot size={18} /> Warehouse Operation Copilot</div>
          <h1>AI decision platform for frontline warehouse operations</h1>
          <p>Powered by LangGraph ReAct orchestration, the agent dynamically calls data processing, simulation, anomaly diagnosis, and equipment control Skills through an MCP safety boundary for WMS interaction.</p>
        </div>
        <div className="architecture-card">
          <div><Database /> Perception Layer</div>
          <span />
          <div><Bot /> Cognition Layer</div>
          <span />
          <div><ShieldCheck /> MCP Safety Interaction</div>
        </div>
      </section>

      {error && <div className="error">{error}</div>}

      <section className="kpi-grid">
        {kpis.map((item) => (
          <article className={`kpi ${item.tone}`} key={item.label}>
            <item.icon size={22} />
            <div>
              <p>{item.label}</p>
              <strong>{item.value}</strong>
            </div>
          </article>
        ))}
      </section>

      <section className="workspace">
        <div className="panel command-panel">
          <div className="panel-header">
            <h2>Operation Task</h2>
            <span>ReAct Task</span>
          </div>
          <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />
          <button onClick={runAgent} disabled={loading || !question.trim()}>
            <Play size={18} /> {loading ? 'Agent reasoning...' : 'Run Agent'}
          </button>
        </div>

        <div className="panel result-panel">
          <div className="panel-header">
            <h2>Decision Output</h2>
            {result && <span>Task {result.task_id.slice(0, 8)}</span>}
          </div>
          {result ? (
            <>
              <div className="answer">{result.answer}</div>
              <h3>Recommendations</h3>
              <ul className="clean-list">
                {result.recommendations.map((item) => <li key={item}><CheckCircle2 size={16} />{item}</li>)}
              </ul>
              <h3>Risk Alerts</h3>
              <ul className="clean-list risk-list">
                {result.risks.map((item) => <li key={item}><AlertTriangle size={16} />{item}</li>)}
              </ul>
            </>
          ) : (
            <div className="placeholder">Enter an operation question and run the agent to view recommendations, risks, and control actions.</div>
          )}
        </div>
      </section>

      {result && (
        <section className="details-grid">
          <div className="panel">
            <div className="panel-header"><h2>LangGraph Trace</h2><span>{result.steps.length} steps</span></div>
            <div className="timeline">
              {result.steps.map((step, index) => (
                <article className="step" key={`${step.name}-${index}`}>
                  <b>{index + 1}. {step.name}</b>
                  <p>{step.thought}</p>
                  <code>{step.action}</code>
                </article>
              ))}
            </div>
          </div>
          <div className="panel">
            <div className="panel-header"><h2>Evaluation Loop</h2><span>Evaluation</span></div>
            <div className="metric-list">
              {Object.entries(result.metrics).map(([key, value]) => (
                <div key={key}><span>{key}</span><strong>{value}</strong></div>
              ))}
            </div>
            <h3>MCP Actions</h3>
            <pre>{JSON.stringify(result.next_actions, null, 2)}</pre>
          </div>
        </section>
      )}
    </main>
  );
}

export default App;
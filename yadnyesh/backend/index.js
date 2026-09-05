/**
 * Smart SOC — Target Website Backend API
 * ========================================
 * Node.js / Express server with Supabase integration.
 *
 * Endpoints:
 *   GET  /health             → Status check
 *   POST /api/login          → Handle login (logs every attempt to Supabase)
 *   GET  /api/attempts       → Fetch recent login attempts (for dashboard)
 *   POST /api/incident       → Receive incident from Decision Engine → save + alert
 *   GET  /api/incidents      → Fetch all incidents
 *   GET  /api/alerts         → Fetch unacknowledged alerts
 *   PUT  /api/alerts/:id     → Acknowledge an alert
 *
 * Run: npm run dev
 */

import 'dotenv/config';
import express   from 'express';
import cors      from 'cors';
import { createClient } from '@supabase/supabase-js';
import bcrypt    from 'bcryptjs';

const app  = express();
const PORT = process.env.PORT || 3001;

// ─────────────────────────────────────────────
// Supabase client (uses service role key for full access)
// ─────────────────────────────────────────────
const supabase = createClient(
  process.env.SUPABASE_URL        || '',
  process.env.SUPABASE_SERVICE_KEY || ''
);

// ─────────────────────────────────────────────
// Middleware
// ─────────────────────────────────────────────
app.use(cors({ origin: process.env.FRONTEND_URL || 'http://localhost:5173' }));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Request logger (shows in terminal when simulation attacks)
app.use((req, _res, next) => {
  const now = new Date().toISOString();
  process.stdout.write(`\r[${now}] ${req.method} ${req.path}          `);
  next();
});

// ─────────────────────────────────────────────
// ROUTE: Health check
// ─────────────────────────────────────────────
app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'Smart SOC Target API', port: PORT });
});

// ─────────────────────────────────────────────
// ROUTE: POST /api/register
// ─────────────────────────────────────────────
app.post('/api/register', async (req, res) => {
  const { username = '', password = '' } = req.body;

  if (!username || !password) {
    return res.status(400).json({ status: 'error', message: 'Username and password required.' });
  }

  // Check if user exists
  const { data: existingUser } = await supabase
    .from('users')
    .select('id')
    .eq('username', username)
    .single();

  if (existingUser) {
    return res.status(409).json({ status: 'error', message: 'Username already taken.' });
  }

  // Hash password and store
  const salt = await bcrypt.genSalt(10);
  const password_hash = await bcrypt.hash(password, salt);

  const { error } = await supabase
    .from('users')
    .insert({ username, password_hash });

  if (error) {
    return res.status(500).json({ status: 'error', message: 'Database error.', details: error.message });
  }

  return res.status(201).json({ status: 'success', message: 'Registration successful!' });
});

// ─────────────────────────────────────────────
// ROUTE: POST /api/login
// The login endpoint attacked by bruteforce_simulation.py
// Logs every attempt to Supabase: login_attempts table
// ─────────────────────────────────────────────
app.post('/api/login', async (req, res) => {
  const { username = '', password = '' } = req.body;
  const ip        = req.ip || req.headers['x-forwarded-for'] || '127.0.0.1';
  const userAgent = req.headers['user-agent'] || 'unknown';

  let success = false;
  let status_code = 401;
  let message = 'Invalid credentials.';

  // Check the database
  const { data: user } = await supabase
    .from('users')
    .select('password_hash')
    .eq('username', username)
    .single();

  if (user) {
    const isMatch = await bcrypt.compare(password, user.password_hash);
    if (isMatch) {
      success = true;
      status_code = 200;
      message = 'Login successful!';
    }
  }

  // Log the attempt to Supabase (non-blocking — don't await so it stays fast)
  supabase
    .from('login_attempts')
    .insert({ username, ip_address: ip, success, status_code, user_agent: userAgent })
    .then(({ error }) => {
      if (error) console.error('\n[DB Error]', error.message);
    });

  if (success) {
    return res.status(200).json({ status: 'success', message });
  }

  return res.status(401).json({ status: 'error', message });
});

// ─────────────────────────────────────────────
// ROUTE: GET /api/attempts
// Returns recent login attempts (for the SOC dashboard / debugging)
// ─────────────────────────────────────────────
app.get('/api/attempts', async (_req, res) => {
  const { data, error } = await supabase
    .from('login_attempts')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(100);

  if (error) return res.status(500).json({ error: error.message });
  res.json({ attempts: data, count: data.length });
});

// ─────────────────────────────────────────────
// ROUTE: POST /api/incident
// Called by the Decision Engine (or bruteforce_simulation.py Stage 3)
// Saves the incident and creates an alert if analyst is required
// ─────────────────────────────────────────────
app.post('/api/incident', async (req, res) => {
  const {
    incident_id, attack_type, src_ip, confidence, risk_score,
    severity, priority, automation_level, playbook,
    incident_status, analyst_required
  } = req.body;

  // Upsert incident
  const { error: incidentErr } = await supabase
    .from('incidents')
    .upsert({
      incident_id, attack_type, src_ip, confidence, risk_score,
      severity, priority, automation_level, playbook,
      incident_status, analyst_required
    }, { onConflict: 'incident_id' });

  if (incidentErr) {
    return res.status(500).json({ error: incidentErr.message });
  }

  // If analyst is required → create a human alert
  if (analyst_required) {
    await supabase.from('alerts').insert({
      incident_id,
      message: `⚠️ Human review required for ${attack_type} attack from ${src_ip}. Risk: ${risk_score}`,
      severity: severity || 'HIGH',
    });
  }

  res.json({ status: 'saved', incident_id, analyst_required });
});

// ─────────────────────────────────────────────
// ROUTE: GET /api/incidents
// Returns all incidents ordered by most recent
// ─────────────────────────────────────────────
app.get('/api/incidents', async (_req, res) => {
  const { data, error } = await supabase
    .from('incidents')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(50);

  if (error) return res.status(500).json({ error: error.message });
  res.json({ incidents: data });
});

// ─────────────────────────────────────────────
// ROUTE: GET /api/alerts
// Returns all unacknowledged alerts
// ─────────────────────────────────────────────
app.get('/api/alerts', async (_req, res) => {
  const { data, error } = await supabase
    .from('alerts')
    .select('*, incidents(*)')
    .eq('acknowledged', false)
    .order('created_at', { ascending: false });

  if (error) return res.status(500).json({ error: error.message });
  res.json({ alerts: data });
});

// ─────────────────────────────────────────────
// ROUTE: PUT /api/alerts/:id
// Analyst acknowledges an alert
// ─────────────────────────────────────────────
app.put('/api/alerts/:id', async (req, res) => {
  const { id } = req.params;
  const { acknowledged_by = 'Analyst' } = req.body;

  const { error } = await supabase
    .from('alerts')
    .update({ acknowledged: true, acknowledged_by, acknowledged_at: new Date().toISOString() })
    .eq('id', id);

  if (error) return res.status(500).json({ error: error.message });
  res.json({ status: 'acknowledged', id });
});

// ─────────────────────────────────────────────
// START
// ─────────────────────────────────────────────
app.listen(PORT, async () => {
  console.log('='.repeat(55));
  console.log('  Smart SOC — Target Website Backend API');
  console.log('='.repeat(55));
  console.log(`  Listening on : http://localhost:${PORT}`);
  console.log(`  Frontend     : ${process.env.FRONTEND_URL || 'http://localhost:5173'}`);
  console.log(`  Supabase     : ${process.env.SUPABASE_URL ? '✓ Connected' : '⚠ Not configured (fill .env)'}`);
  console.log('='.repeat(55));

  // Seed default admin user for simulation if not exists
  const { data: adminUser } = await supabase.from('users').select('id').eq('username', 'admin').single();
  if (!adminUser) {
    console.log('  [Init] Seeding default admin user...');
    const salt = await bcrypt.genSalt(10);
    const password_hash = await bcrypt.hash('secretpassword123', salt);
    await supabase.from('users').insert({ username: 'admin', password_hash });
    console.log('  [Init] Default admin user created.');
  }
});

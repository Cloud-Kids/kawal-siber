#!/usr/bin/env node
/**
 * start-standalone.js — Cross-platform standalone production runner for KAWAL SIBER.
 *
 * In accordance with Next.js 15 standalone output specification:
 * 1. Validates presence of .next/standalone/server.js.
 * 2. Synchronizes public/ and .next/static/ into .next/standalone/ for static asset serving.
 * 3. Enforces loopback binding HOSTNAME=127.0.0.1 by default for localhost Windows preview.
 * 4. Defaults PORT=3000 while honoring explicit overrides.
 * 5. Preserves environment variables, forwards termination signals, and propagates exit codes.
 */

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const frontendDir = path.resolve(__dirname, '..');
const standaloneDir = path.join(frontendDir, '.next', 'standalone');
const serverPath = path.join(standaloneDir, 'server.js');

// 1. Verify standalone build artifact
if (!fs.existsSync(serverPath)) {
  console.error('\n[ERROR] Next.js standalone server artifact not found at:');
  console.error(`  ${serverPath}`);
  console.error('\nPlease run "npm run build" first to generate the standalone artifact.\n');
  process.exit(1);
}

// 2. Synchronize static assets into standalone folder (as required by Next.js documentation)
try {
  const srcStatic = path.join(frontendDir, '.next', 'static');
  const destStatic = path.join(standaloneDir, '.next', 'static');
  if (fs.existsSync(srcStatic)) {
    fs.mkdirSync(path.dirname(destStatic), { recursive: true });
    fs.cpSync(srcStatic, destStatic, { recursive: true, force: true });
  }

  const srcPublic = path.join(frontendDir, 'public');
  const destPublic = path.join(standaloneDir, 'public');
  if (fs.existsSync(srcPublic)) {
    fs.mkdirSync(destPublic, { recursive: true });
    fs.cpSync(srcPublic, destPublic, { recursive: true, force: true });
  }
} catch (copyErr) {
  console.warn(`[WARN] Failed to sync static assets to standalone: ${copyErr.message}`);
}

// 3. Resolve host and port configuration
const hostname = process.env.HOSTNAME || '127.0.0.1';
const port = process.env.PORT || '3000';

const env = {
  ...process.env,
  NODE_ENV: 'production',
  HOSTNAME: hostname,
  PORT: String(port),
};

console.log(`Starting Next.js standalone production preview on http://${hostname}:${port}...`);

// 4. Spawn standalone server child process
const child = spawn(process.execPath, [serverPath], {
  cwd: standaloneDir,
  env,
  stdio: 'inherit',
});

// 5. Forward OS process signals
const forwardSignal = (signal) => {
  if (child && !child.killed) {
    child.kill(signal);
  }
};

process.on('SIGINT', () => forwardSignal('SIGINT'));
process.on('SIGTERM', () => forwardSignal('SIGTERM'));

// 6. Propagate child process exit code
child.on('close', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
  } else {
    process.exit(code ?? 0);
  }
});


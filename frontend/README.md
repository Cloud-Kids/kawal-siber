# KAWAL SIBER — Frontend Component

## 1. Purpose & Architecture

The **KAWAL SIBER Frontend** provides the command-and-control user interface for territorial cyber defense operations. Built on **Next.js 15 App Router** and **React 19**, it interfaces with the backend API to visualize assets, network topologies, intrusion detection telemetry (Suricata), incident intelligence, AI triage assessments, and cryptographic security reports.

### Key Architecture Characteristics:
- **Server and Client Component Split**: Uses React Server Components (RSC) where appropriate, with dynamic interactive client views for real-time telemetry.
- **Standalone Production Output**: Configured with `output: 'standalone'` in `next.config.ts`, producing an optimized, minimal Node.js server bundle.
- **Loopback-First Development**: Binds explicitly to `127.0.0.1` during local development to avoid accidental exposure on public network interfaces.
- **22 Pre-compiled Routes**: Covers Assets, Dashboard, Monitoring (Alerts, Events, PCAP, Scans), Scopes, Web Security (Targets, Assessments, Findings), Intelligence, Analytics, and Cryptographic Reporting.

---

## 2. Requirements & Dependencies

- **Node.js**: `v20.x` or `v22.x LTS` (Verified with Node.js `v24.21.0` and `v22.9.0`).
- **npm**: `v10.x` or higher.
- **Next.js**: `15.3.3`
- **React / React DOM**: `19.1.0`
- **TypeScript**: `5.6.3`
- **Tailwind CSS**: `3.4.15`
- **Lucide React**: `0.460.0` (Cybersecurity and dashboard iconography)

---

## 3. Installation

From the `frontend` directory:

```bash
# Clean, deterministic installation based on package-lock.json
npm ci
```

---

## 4. Environment Configuration

Create or update `.env.local` (excluded from Git):

```ini
# Internal API URL for Server-Side Rendering (SSR) & API route proxy
API_INTERNAL_URL=http://127.0.0.1:8000

# Public API prefix for client-side fetches
NEXT_PUBLIC_API_URL=/api/v1

# Development socket binding
PORT=3000
HOSTNAME=127.0.0.1

# Telemetry
NEXT_TELEMETRY_DISABLED=1
```

---

## 5. Development & Production Operations

### Local Development Server
Starts Next.js with explicit loopback binding (`127.0.0.1:3000`):

```bash
npm run dev
```

### Type Checking & Linting
```bash
# TypeScript strict type checking without emitting JS
npm run type-check

# ESLint inspection
npm run lint
```

### Production Build
Compiles all 22 user routes and outputs the standalone artifact to `.next/standalone`:

```bash
npm run build
```

### Production Standalone Startup
Starts the standalone server via [`scripts/start-standalone.js`](./scripts/start-standalone.js), which automatically synchronizes static assets (`.next/static` and `public`) into the standalone directory:

```bash
npm start
```

---

## 6. Docker Containerization

The frontend container is built using a 3-stage minimal `node:22-alpine` image:

```bash
# Build the container image
docker build -t kawal-siber-frontend:latest -f Dockerfile .

# Run the container (production port 3000)
docker run -d \
  --name frontend \
  -p 127.0.0.1:3000:3000 \
  -e NODE_ENV=production \
  -e API_INTERNAL_URL=http://backend:8000 \
  kawal-siber-frontend:latest
```

---

## 7. Troubleshooting & Common Pitfalls

1. **Port 3000 in Use**:
   - Check listening process: `netstat -ano | findstr :3000` (Windows) or `lsof -i :3000` (Linux).
   - Terminate lingering Node process or change `PORT=3001`.
2. **Static Asset 404 in Standalone Mode**:
   - Always run via `node scripts/start-standalone.js` or ensure `.next/static` and `public` are copied into `.next/standalone`.
3. **Backend API Connection Refused**:
   - Verify backend is running on `127.0.0.1:8000`: `curl http://127.0.0.1:8000/api/v1/health`.
   - Ensure `API_INTERNAL_URL` is correctly configured in `.env.local`.

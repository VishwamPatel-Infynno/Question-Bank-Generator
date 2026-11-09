import { execSync } from 'node:child_process';

const TARGET_PORTS = [8000, 5173];

function cleanPorts() {
  if (process.platform === 'win32') {
    for (const port of TARGET_PORTS) {
      try {
        const out = execSync(`netstat -ano -p tcp | findstr :${port}`, {
          encoding: 'utf8',
          stdio: ['pipe', 'pipe', 'ignore'],
        });
        const lines = out.trim().split(/\r?\n/);
        for (const line of lines) {
          const parts = line.trim().split(/\s+/);
          // Format: TCP  LocalAddress  ForeignAddress  State  PID
          if (parts.length >= 5 && parts[1].endsWith(`:${port}`)) {
            const pid = parts[parts.length - 1];
            if (pid && pid !== '0' && pid !== String(process.pid)) {
              try {
                execSync(`taskkill /F /PID ${pid}`, { stdio: 'ignore' });
                console.log(`[clean-ports] Released port ${port} (PID: ${pid})`);
              } catch {
                // Ignore permission or already terminated
              }
            }
          }
        }
      } catch {
        // Port is free (findstr returned 1)
      }
    }
  } else {
    for (const port of TARGET_PORTS) {
      try {
        execSync(`lsof -ti :${port} | xargs kill -9 2>/dev/null || true`, {
          stdio: 'ignore',
          shell: '/bin/sh',
        });
      } catch {
        // Ignore if port not in use or lsof not installed
      }
    }
  }
}

try {
  cleanPorts();
} catch {
  // Always exit cleanly
}
process.exit(0);

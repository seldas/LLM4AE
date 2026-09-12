const cp = require('child_process');
const fs = require('fs');
const path = require('path');

const isWin = process.platform === 'win32';

// Resolve project root from client/scripts directory
const projectRoot = path.resolve(__dirname, '..', '..');
const serverApp = path.resolve(projectRoot, 'server', 'app.py');

let pythonCmd;

if (isWin) {
    // Windows: Check root venv first, then system python
    const venvPath = path.resolve(projectRoot, 'venv', 'Scripts', 'python.exe');
    pythonCmd = fs.existsSync(venvPath) ? venvPath : 'python';
} else {
    // Linux/macOS: Check server/.venv first, then fallback to system python3
    const venvPath = path.resolve(projectRoot, 'server', '.venv', 'bin', 'python');
    pythonCmd = fs.existsSync(venvPath) ? venvPath : 'python3';
}

console.log(`Starting server with: ${pythonCmd} ${serverApp}`);

const serverProcess = cp.spawn(pythonCmd, [serverApp], {
    stdio: 'inherit',
    shell: true
});

serverProcess.on('error', (err) => {
    console.error(`Failed to start server: ${err.message}`);
    process.exit(1);
});

serverProcess.on('exit', (code) => {
    process.exit(code || 0);
});

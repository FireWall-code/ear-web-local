const { WebSocketServer } = require('ws');
const { SerialPort } = require('serialport');

const BRIDGE_PORT = 8765;
const MANUAL_PORT = process.argv[2] || null;

const wss = new WebSocketServer({ port: BRIDGE_PORT });
let activePort = null;
let btConnected = false;
const clients = new Set();

// Serial number request (command 0xC006, operationID=1, CRC pre-calculated)
const TEST_CMD = Buffer.from('55600106c0000001911f', 'hex');
// Battery request (command 0xC007, operationID=1)
const BATTERY_CMD = Buffer.from('55600107c00000019e2f', 'hex');

console.log('=== Ear Web Bridge ===');
console.log(`WebSocket démarré sur ws://localhost:${BRIDGE_PORT}\n`);

function broadcast(data) {
    clients.forEach(ws => {
        if (ws.readyState === 1) ws.send(data);
    });
}

async function findResponsivePort(portPaths) {
    console.log('Ouverture des ports Bluetooth en parallèle...');

    return new Promise((resolve) => {
        const openedPorts = new Map();
        let pending = portPaths.length;
        let resolved = false;

        function usePort(path) {
            if (resolved) return;
            resolved = true;
            console.log(`\nNothing Ear trouvé sur ${path} !`);
            for (const [p, port] of openedPorts) {
                if (p !== path) {
                    try { port.close(); } catch(e) {}
                }
            }
            resolve(openedPorts.get(path));
        }

        portPaths.forEach(path => {
            const port = new SerialPort({ path, baudRate: 9600, autoOpen: false });

            port.on('error', (e) => {
                console.log(`  ${path} error:`, e.message);
            });

            port.on('data', (data) => {
                console.log(`← ${path}:`, Buffer.from(data).toString('hex'));
                if (!resolved && data[0] === 0x55) {
                    usePort(path);
                }
            });

            port.open((err) => {
                if (err) {
                    console.log(`  ${path}: Échec (${err.message})`);
                } else {
                    console.log(`  ${path}: Ouvert`);
                    openedPorts.set(path, port);
                    port.write(TEST_CMD);
                    setTimeout(() => {
                        if (!resolved && openedPorts.has(path)) {
                            port.write(BATTERY_CMD);
                        }
                    }, 1000);
                }
                pending--;
                if (pending === 0 && openedPorts.size === 0) {
                    resolve(null);
                }
            });
        });

        // Timeout : si personne ne répond, utiliser le premier port ouvert comme fallback
        setTimeout(() => {
            if (!resolved) {
                if (openedPorts.size > 0) {
                    const firstPath = [...openedPorts.keys()][0];
                    console.log(`\nAucune réponse reçue. Utilisation de ${firstPath} (fallback)`);
                    usePort(firstPath);
                } else {
                    resolve(null);
                }
            }
        }, 6000);
    });
}

async function init() {
    let port = null;

    if (MANUAL_PORT) {
        console.log(`Connexion sur ${MANUAL_PORT}...`);
        port = await new Promise((resolve) => {
            const p = new SerialPort({ path: MANUAL_PORT, baudRate: 9600, autoOpen: false });
            p.open(err => resolve(err ? null : p));
        });
    } else {
        const ports = await SerialPort.list();
        console.log('Ports série disponibles:');
        ports.forEach(p => console.log(`  ${p.path} - ${p.friendlyName || p.manufacturer || 'inconnu'}`));

        const btPorts = ports.filter(p => {
            const name = (p.friendlyName || p.manufacturer || '').toLowerCase();
            const pnp = (p.pnpId || '').toUpperCase();
            return name.includes('bluetooth') || pnp.includes('BTHENUM');
        });

        if (btPorts.length === 0) {
            console.log('\nAucun port Bluetooth COM trouvé.');
            console.log('Astuce: node bridge.js COM3');
            return;
        }

        port = await findResponsivePort(btPorts.map(p => p.path));
    }

    if (!port) {
        console.log('\nImpossible de se connecter. Essayez: node bridge.js COM3');
        return;
    }

    activePort = port;
    btConnected = true;
    console.log('Connecté !');
    console.log('Ouvrez http://localhost:3000 dans Chrome puis cliquez Connect\n');

    broadcast(JSON.stringify({ type: 'connected' }));

    activePort.on('data', (data) => {
        console.log('← Reçu:', Buffer.from(data).toString('hex'));
        broadcast(Buffer.from(data));
    });

    activePort.on('close', () => {
        btConnected = false;
        console.log('Port fermé / Nothing Ear déconnecté');
        broadcast(JSON.stringify({ type: 'disconnected' }));
    });

    activePort.on('error', (err) => {
        console.error('Erreur port:', err.message);
    });
}

wss.on('connection', (ws) => {
    clients.add(ws);
    console.log('Navigateur connecté');
    ws.send(JSON.stringify({ type: btConnected ? 'connected' : 'connecting' }));

    ws.on('message', (data) => {
        if (activePort && activePort.isOpen) {
            const buf = Buffer.from(data);
            console.log('→ Envoyé:', buf.toString('hex'));
            activePort.write(buf, (err) => {
                if (err) console.error('Erreur écriture:', err);
            });
        }
    });

    ws.on('close', () => {
        clients.delete(ws);
        console.log('Navigateur déconnecté');
    });
});

init();

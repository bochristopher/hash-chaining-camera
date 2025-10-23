/**
 * Provenance Logger Dashboard - Client-side JavaScript
 */

const API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:5000'
    : `http://${window.location.hostname}:5000`;

let updateInterval = null;

// Initialize dashboard
async function init() {
    console.log('Initializing Provenance Logger Dashboard');
    console.log('API endpoint:', API_BASE);

    // Load initial data
    await updateStatus();
    await updateChain();
    await updateLatestFrame();

    // Start auto-update (every 3 seconds)
    updateInterval = setInterval(async () => {
        await updateStatus();
        await updateLatestFrame();
        await updateChain();
    }, 3000);
}

// Update system status
async function updateStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/status`);
        const data = await response.json();

        document.getElementById('system-status').textContent = data.status;
        document.getElementById('chain-length').textContent = data.chain_length;

        if (data.latest_entry) {
            const timestamp = new Date(data.latest_entry.timestamp).toLocaleString();
            document.getElementById('last-update').textContent = timestamp;
        }

        // Update status color
        const statusEl = document.getElementById('system-status');
        statusEl.className = data.status === 'online' ? 'status-value' : 'status-value error';

    } catch (error) {
        console.error('Status update error:', error);
        document.getElementById('system-status').textContent = 'Offline';
        document.getElementById('system-status').className = 'status-value error';
    }
}

// Update latest frame image
async function updateLatestFrame() {
    try {
        const img = document.getElementById('latest-frame');
        // Add timestamp to prevent caching
        img.src = `${API_BASE}/api/latest-frame?t=${Date.now()}`;
        img.onerror = () => {
            img.alt = 'No frames captured yet';
        };
    } catch (error) {
        console.error('Frame update error:', error);
    }
}

// Update chain log
async function updateChain() {
    try {
        const response = await fetch(`${API_BASE}/api/chain?limit=20`);
        const data = await response.json();

        const chainLog = document.getElementById('chain-log');

        if (data.entries.length === 0) {
            chainLog.innerHTML = '<div class="loading">No chain entries yet</div>';
            return;
        }

        // Reverse to show newest first
        const entries = data.entries.reverse();

        chainLog.innerHTML = entries.map(entry => `
            <div class="chain-entry">
                <div>
                    <span class="chain-index">#${String(entry.index).padStart(4, '0')}</span>
                    <span class="chain-timestamp">${new Date(entry.timestamp).toLocaleString()}</span>
                </div>
                <div class="chain-hash">
                    Frame: ${entry.frame_hash.substring(0, 16)}...
                </div>
                <div class="chain-hash">
                    Entry: ${entry.entry_hash.substring(0, 16)}...
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Chain update error:', error);
        document.getElementById('chain-log').innerHTML =
            '<div class="error">Failed to load chain data</div>';
    }
}

// Verify chain integrity
async function verifyChain() {
    const button = document.querySelector('.verify-button');
    const resultDiv = document.getElementById('verify-result');

    button.disabled = true;
    button.textContent = 'Verifying...';
    resultDiv.innerHTML = '<div class="loading">Running verification...</div>';

    try {
        const response = await fetch(`${API_BASE}/api/verify`);
        const result = await response.json();

        if (result.valid) {
            resultDiv.innerHTML = `
                <div class="success">
                    <strong>VERIFICATION PASSED</strong><br>
                    All ${result.verified_entries} entries verified successfully.<br>
                    Verification time: ${result.verification_time}
                </div>
            `;
        } else {
            resultDiv.innerHTML = `
                <div class="error">
                    <strong>VERIFICATION FAILED</strong><br>
                    Failed: ${result.failed_entries}/${result.total_entries} entries<br>
                    ${result.failures.map(f =>
                        `Entry #${f.entry_index}: ${f.reason}`
                    ).join('<br>')}
                </div>
            `;
        }

    } catch (error) {
        console.error('Verification error:', error);
        resultDiv.innerHTML = `
            <div class="error">
                <strong>Verification request failed</strong><br>
                ${error.message}
            </div>
        `;
    } finally {
        button.disabled = false;
        button.textContent = 'Verify Chain Integrity';
    }
}

// Start dashboard when page loads
window.addEventListener('load', init);

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (updateInterval) {
        clearInterval(updateInterval);
    }
});

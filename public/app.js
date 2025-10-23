class HashChainDashboard {
    constructor() {
        this.eventSource = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 2000;

        this.elements = {
            preview: document.getElementById('preview'),
            chainLog: document.getElementById('chain-log'),
            statusIndicator: document.getElementById('status-indicator'),
            tamperBtn: document.getElementById('tamper-btn'),
            connectionStatus: document.getElementById('connection-status')
        };

        this.init();
    }

    init() {
        this.setupEventSource();
        this.setupImageRefresh();
        this.setupTamperButton();
        this.clearChainLog();
    }

    setupEventSource() {
        this.updateConnectionStatus('connecting');

        try {
            this.eventSource = new EventSource('/events');

            this.eventSource.onopen = () => {
                console.log('SSE connection established');
                this.updateConnectionStatus('connected');
                this.reconnectAttempts = 0;
            };

            this.eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleServerEvent(data);
                } catch (err) {
                    console.error('Failed to parse SSE data:', err);
                }
            };

            this.eventSource.onerror = (error) => {
                console.error('SSE connection error:', error);
                this.updateConnectionStatus('disconnected');

                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    setTimeout(() => {
                        console.log(`Attempting to reconnect (${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`);
                        this.reconnectAttempts++;
                        this.setupEventSource();
                    }, this.reconnectDelay);
                }
            };

        } catch (error) {
            console.error('Failed to establish SSE connection:', error);
            this.updateConnectionStatus('disconnected');
        }
    }

    handleServerEvent(data) {
        console.log('Server event:', data);

        switch (data.type) {
            case 'connected':
                this.updateConnectionStatus('connected');
                break;

            case 'chain_head':
                this.addChainEntry({
                    index: data.index,
                    timestamp: data.timestamp,
                    frame: data.frame,
                    hash: data.hash
                });
                break;

            case 'verify_ok':
                this.updateStatus('good', `All good (${data.count} entries verified)`);
                break;

            case 'verify_fail':
                this.updateStatus('error', `Hash mismatch at index ${data.atIndex}`);
                break;

            case 'tampered':
                this.showTamperNotification(data.file);
                break;

            case 'error':
                console.error('Server error:', data.message);
                this.updateStatus('error', `Error: ${data.message}`);
                break;

            default:
                console.log('Unknown event type:', data.type);
        }
    }

    addChainEntry(entry) {
        // Remove loading message if present
        const loading = this.elements.chainLog.querySelector('.loading');
        if (loading) {
            loading.remove();
        }

        // Check if entry with this index already exists
        const existingEntry = this.elements.chainLog.querySelector(`[data-index="${entry.index}"]`);
        if (existingEntry) {
            console.log(`Entry with index ${entry.index} already exists, skipping duplicate`);
            return;
        }

        const entryElement = document.createElement('div');
        entryElement.className = 'chain-entry';
        entryElement.setAttribute('data-index', entry.index);

        const timestamp = new Date(entry.timestamp);
        const timeString = timestamp.toLocaleTimeString();

        entryElement.innerHTML = `
            <div class="chain-info">
                <div>
                    <span class="chain-index">#${entry.index}</span>
                    <span class="chain-timestamp">${timeString}</span>
                </div>
                <div style="font-size: 0.8em; color: #888; margin-top: 3px;">
                    ${entry.frame}
                </div>
            </div>
            <div class="chain-hash">${entry.hash.slice(0, 12)}...</div>
        `;

        // Add new entry at the top
        this.elements.chainLog.insertBefore(entryElement, this.elements.chainLog.firstChild);

        // Limit to 50 entries to prevent memory issues
        const entries = this.elements.chainLog.querySelectorAll('.chain-entry');
        if (entries.length > 50) {
            entries[entries.length - 1].remove();
        }

        // Animate in
        entryElement.style.opacity = '0';
        entryElement.style.transform = 'translateX(-20px)';
        setTimeout(() => {
            entryElement.style.transition = 'all 0.3s ease';
            entryElement.style.opacity = '1';
            entryElement.style.transform = 'translateX(0)';
        }, 50);
    }

    updateStatus(type, message) {
        this.elements.statusIndicator.className = `status-indicator status-${type}`;
        this.elements.statusIndicator.textContent = message;
    }

    updateConnectionStatus(status) {
        const statusElement = this.elements.connectionStatus;
        statusElement.className = `connection-status ${status}`;

        switch (status) {
            case 'connecting':
                statusElement.textContent = 'Connecting to server...';
                break;
            case 'connected':
                statusElement.textContent = 'Connected';
                // Hide after 3 seconds
                setTimeout(() => {
                    statusElement.style.opacity = '0';
                }, 3000);
                break;
            case 'disconnected':
                statusElement.textContent = 'Connection lost';
                statusElement.style.opacity = '1';
                break;
        }
    }

    setupImageRefresh() {
        // Refresh preview image every 1.5 seconds
        setInterval(() => {
            this.refreshPreview();
        }, 1500);

        // Also refresh on image error
        this.elements.preview.onerror = () => {
            setTimeout(() => this.refreshPreview(), 1000);
        };
    }

    refreshPreview() {
        const timestamp = Date.now();
        this.elements.preview.src = `/latest.jpg?ts=${timestamp}`;
    }

    setupTamperButton() {
        this.elements.tamperBtn.addEventListener('click', async () => {
            this.elements.tamperBtn.disabled = true;
            this.elements.tamperBtn.textContent = 'Tampering...';

            try {
                const response = await fetch('/tamper', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                const result = await response.json();

                if (result.success) {
                    console.log('Tamper successful:', result.file);
                } else {
                    console.error('Tamper failed:', result.error);
                    this.updateStatus('error', `Tamper failed: ${result.error}`);
                }
            } catch (error) {
                console.error('Tamper request failed:', error);
                this.updateStatus('error', 'Failed to tamper frame');
            } finally {
                this.elements.tamperBtn.disabled = false;
                this.elements.tamperBtn.textContent = 'Tamper a Frame';
            }
        });
    }

    showTamperNotification(filename) {
        // Create temporary notification
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #ff6b35;
            color: white;
            padding: 20px 30px;
            border-radius: 10px;
            font-weight: bold;
            z-index: 10000;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            animation: pulse 0.5s ease-in-out;
        `;
        notification.textContent = `Tampered with ${filename}`;

        document.body.appendChild(notification);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => document.body.removeChild(notification), 300);
        }, 3000);
    }

    clearChainLog() {
        this.elements.chainLog.innerHTML = `
            <div class="chain-entry loading">
                <span>Waiting for first frame...</span>
            </div>
        `;
    }

    destroy() {
        if (this.eventSource) {
            this.eventSource.close();
        }
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new HashChainDashboard();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.dashboard) {
        window.dashboard.destroy();
    }
});
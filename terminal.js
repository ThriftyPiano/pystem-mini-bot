/**
 * Serial Terminal for ESP32 Robot Car
 * Displays WebSerial communication for debugging
 */

class SerialTerminal {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.isVisible = false;
        this.maxLines = 1000; // Maximum number of lines to keep
        this.autoScroll = true;
        this.init();
    }

    init() {
        this.container.innerHTML = `
            <div class="terminal-header">
                <span class="terminal-title">Serial Monitor</span>
                <div class="terminal-controls">
                    <button class="terminal-btn" id="terminal-clear">Clear</button>
                    <button class="terminal-btn" id="terminal-autoscroll">Auto-scroll: ON</button>
                </div>
            </div>
            <div class="terminal-content" id="terminal-output" tabindex="0"></div>
        `;

        this.output = document.getElementById('terminal-output');
        
        this.setupEventListeners();
        this.setupStyles();
    }

    setupStyles() {
        if (!document.getElementById('terminal-styles')) {
            const style = document.createElement('style');
            style.id = 'terminal-styles';
            style.textContent = `
                .terminal-container {
                    display: flex;
                    flex-direction: column;
                    background: #1e1e1e;
                    color: #d4d4d4;
                    font-family: 'Courier New', monospace;
                    font-size: 12px;
                    height: 100%;
                    min-width: 300px;
                    border-left: 1px solid #333;
                }
                
                .terminal-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 8px 12px;
                    background: #2d2d30;
                    border-bottom: 1px solid #333;
                    font-size: 13px;
                }
                
                .terminal-title {
                    font-weight: bold;
                    color: #cccccc;
                }
                
                .terminal-controls {
                    display: flex;
                    gap: 4px;
                }
                
                .terminal-btn {
                    padding: 4px 8px;
                    font-size: 11px;
                    border: 1px solid #555;
                    background: #3c3c3c;
                    color: #cccccc;
                    border-radius: 2px;
                    cursor: pointer;
                    font-family: inherit;
                }
                
                .terminal-btn:hover {
                    background: #4c4c4c;
                }
                
                .terminal-content {
                    flex: 1;
                    overflow-y: auto;
                    padding: 8px;
                    background: #1e1e1e;
                    white-space: pre-wrap;
                    word-break: break-all;
                    outline: none;
                }
                
                .terminal-input-container {
                    display: none;
                }
                
                .terminal-input {
                    display: none;
                }
                
                .terminal-input:focus {
                    outline: none;
                    border-color: #007acc;
                }
                
                .terminal-line {
                    margin: 0;
                    line-height: 1.4;
                }
                
                .terminal-sent {
                    color: #569cd6;
                }
                
                .terminal-received {
                    color: #d4d4d4;
                }
                
                .terminal-error {
                    color: #f44747;
                }
                
                .terminal-info {
                    color: #4ec9b0;
                }
                
                .terminal-timestamp {
                    color: #808080;
                    font-size: 10px;
                }
            `;
            document.head.appendChild(style);
        }
    }

    setupEventListeners() {
        // Clear button
        document.getElementById('terminal-clear').addEventListener('click', () => {
            this.clear();
        });

        // Auto-scroll toggle
        const autoScrollBtn = document.getElementById('terminal-autoscroll');
        autoScrollBtn.addEventListener('click', () => {
            this.autoScroll = !this.autoScroll;
            autoScrollBtn.textContent = `Auto-scroll: ${this.autoScroll ? 'ON' : 'OFF'}`;
        });

        // Direct keyboard input to serial
        this.output.addEventListener('keydown', (e) => {
            this.handleKeyInput(e);
        });
    }

    addLine(text, type = 'received', includeTimestamp = false) {
        const line = document.createElement('span');
        line.className = `terminal-line terminal-${type}`;
        
        // Just add the raw text without timestamps
        const escapedText = this.escapeHtml(text);
        line.innerHTML = escapedText;
        
        this.output.appendChild(line);
        
        // Limit number of lines
        while (this.output.children.length > this.maxLines) {
            this.output.removeChild(this.output.firstChild);
        }
        
        // Auto-scroll to bottom
        if (this.autoScroll) {
            this.scrollToBottom();
        }
    }

    addRawText(text, type = 'received') {
        // Add text without creating new lines, for real-time character display
        const span = document.createElement('span');
        span.className = `terminal-${type}`;
        span.textContent = text;
        this.output.appendChild(span);
        
        // Limit content
        while (this.output.children.length > this.maxLines) {
            this.output.removeChild(this.output.firstChild);
        }
        
        // Auto-scroll to bottom
        if (this.autoScroll) {
            this.scrollToBottom();
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    scrollToBottom() {
        this.output.scrollTop = this.output.scrollHeight;
    }

    clear() {
        this.output.innerHTML = '';
    }

    handleKeyInput(e) {
        // Send key directly to robot if connected
        if (window.robotSendRaw && typeof window.robotSendRaw === 'function') {
            try {
                let char = '';
                
                // Handle control characters first (Ctrl+key combinations)
                if (e.ctrlKey && !e.altKey && !e.metaKey) {
                    const key = e.key.toLowerCase();
                    if (key.length === 1 && key >= 'a' && key <= 'z') {
                        // Convert Ctrl+A to Ctrl+Z to their control character codes
                        const controlCode = key.charCodeAt(0) - 96; // 'a' = 97, so Ctrl+A = 1, Ctrl+C = 3, etc.
                        char = String.fromCharCode(controlCode);
                        e.preventDefault();
                    }
                }
                // Handle special keys
                else if (e.key === 'Enter') {
                    char = '\r\n';
                } else if (e.key === 'Backspace') {
                    char = '\b';
                } else if (e.key === 'Tab') {
                    char = '\t';
                    e.preventDefault();
                } else if (e.key === 'Escape') {
                    char = '\x1b';
                } else if (e.key.length === 1 && !e.ctrlKey && !e.altKey && !e.metaKey) {
                    // Regular character (only if no modifier keys are pressed)
                    char = e.key;
                } else {
                    // Ignore other special keys (Arrow keys, F keys, etc.)
                    return;
                }
                
                // Show what we're sending (for debugging control characters)
                if (char.charCodeAt(0) < 32) {
                    // Control character - show as readable text
                    const controlName = char.charCodeAt(0) === 3 ? '^C' : 
                                       char.charCodeAt(0) === 4 ? '^D' :
                                       char.charCodeAt(0) === 26 ? '^Z' :
                                       char.charCodeAt(0) === 27 ? '^[' :
                                       `^${String.fromCharCode(char.charCodeAt(0) + 64)}`;
                    // this.addRawText(controlName, 'sent');
                } else {
                    // this.addRawText(char, 'sent');
                }

                // Send to robot
                window.robotSendRaw(char);
                if (char) {
                    e.preventDefault();
                }
            } catch (error) {
                // Silently ignore errors
            }
        }
    }

    show() {
        this.container.style.display = 'flex';
        this.container.classList.add('terminal-container');
        this.isVisible = true;
    }

    hide() {
        this.container.style.display = 'none';
        this.isVisible = false;
    }

    // Methods to be called from robot.js
    logReceived(data) {
        if (typeof data === 'string') {
            this.addRawText(data, 'received');
        } else {
            // Handle binary data
            const decoder = new TextDecoder('utf-8', { ignoreBOM: true, fatal: false });
            const text = decoder.decode(data);
            this.addRawText(text, 'received');
        }
    }
}

// Global terminal instance
let serialTerminal = null;

// Initialize terminal when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Wait a bit to ensure the container exists
    setTimeout(() => {
        const terminalContainer = document.getElementById('terminal-container');
        if (terminalContainer) {
            serialTerminal = new SerialTerminal('terminal-container');
            serialTerminal.show();
            
            // Export to global scope for robot.js to use
            window.serialTerminal = serialTerminal;
        }
    }, 100);
});

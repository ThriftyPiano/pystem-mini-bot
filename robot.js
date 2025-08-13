/**
 * ESP32 Robot Car Communication Interface
 * Extracted from fe_extension.js and kernel.py
 */

class RobotController {
    constructor() {
        this.port = null;
        this.reader = null;
        this.writer = null;
        this.connected = false;
        this.chunkSize = 1024;
        this.lastLineEcho = '';
        
        // Background reading system
        this.serialBuffer = [];
        this.backgroundReadActive = false;
        this.backgroundReadPromise = null;
        this.bufferConsumers = new Set();
        this.lastBufferPosition = 0;
    }

    /**
     * Show WebSerial dialog and connect to selected device
     */
    async connect() {
        if (!('serial' in navigator)) {
            throw new Error('Web Serial API is not supported in this browser');
        }

        try {
            // Request port from user with ESP32 filter
            this.port = await navigator.serial.requestPort({
                filters: [
                    { usbVendorId: 0x1A86, usbProductId: 0x7523 }, // CH340 series
                ]
            });
            
            // Open the serial port
            await this.port.open({ 
                baudRate: 115200,
                dataBits: 8,
                stopBits: 1,
                parity: 'none'
            });

            // Get reader and writer
            this.reader = this.port.readable.getReader();
            this.writer = this.port.writable.getWriter();
            
            this.connected = true;
            
            // Listen for disconnect events (USB unplugged)
            this.port.addEventListener('disconnect', () => {
                console.log('USB device disconnected');
                this.handleUnexpectedDisconnect();
            });
            
            // Start background reading loop
            this.startBackgroundReading();
            
            console.log('Connected to ESP32 device');
            
            // Update UI button states
            this.updateUIButtonStates();
            
            return true;
        } catch (error) {
            // Don't treat user canceling the port selection as an error
            if (error.message && error.message.includes('No port selected by the user')) {
                console.log('User canceled port selection');
                return false;
            }
            
            console.error('Failed to connect:', error);
            throw error;
        }
    }

    /**
     * Disconnect from the device
     */
    async disconnect() {
        try {
            // Stop background reading first
            this.stopBackgroundReading();
            
            if (this.reader) {
                await this.reader.cancel();
                this.reader.releaseLock();
                this.reader = null;
            }
        
            if (this.writer) {
                await this.writer.close();
                this.writer = null;
            }
            
            if (this.port) {
                await this.port.close();
                this.port = null;
            }
            
            this.connected = false;
            
            // Clear buffer
            this.serialBuffer = [];
            this.lastBufferPosition = 0;
            this.bufferConsumers.clear();
            
            console.log('Disconnected from ESP32 device');
            
            // Update UI button states
            this.updateUIButtonStates();
        } catch (error) {
            console.error('Error during disconnect:', error);
            throw error;
        }
    }

    /**
     * Handle unexpected disconnection (e.g., USB unplugged)
     */
    handleUnexpectedDisconnect() {
        try {
            // Stop background reading first
            this.stopBackgroundReading();
            
            // Clean up without trying to close the port (it's already gone)
            this.reader = null;
            this.writer = null;
            this.port = null;
            this.connected = false;
            
            // Clear buffer
            this.serialBuffer = [];
            this.lastBufferPosition = 0;
            this.bufferConsumers.clear();
            
            console.log('ESP32 device disconnected unexpectedly (USB unplugged)');
            
            // Notify the UI if possible
            if (window.serialTerminal) {
                window.serialTerminal.addLine('\n[Device disconnected - USB unplugged]\n', 'error');
            }
            
            // Update UI button states
            this.updateUIButtonStates();
        } catch (error) {
            console.error('Error handling unexpected disconnect:', error);
        }
    }

    /**
     * Start background reading loop that continuously reads from serial
     * and stores data in buffer while also displaying in terminal
     */
    startBackgroundReading() {
        if (this.backgroundReadActive) {
            return;
        }
        
        this.backgroundReadActive = true;
        this.backgroundReadPromise = this.backgroundReadLoop();
    }

    /**
     * Stop background reading loop
     */
    stopBackgroundReading() {
        this.backgroundReadActive = false;
        if (this.backgroundReadPromise) {
            this.backgroundReadPromise = null;
        }
    }

    /**
     * Background reading loop - continuously reads from serial
     */
    async backgroundReadLoop() {
        while (this.backgroundReadActive && this.connected && this.reader) {
            try {
                const readResult = await this.reader.read();
                
                if (readResult.done) {
                    break;
                }
                
                const decoder = new TextDecoder();
                const chunk = decoder.decode(readResult.value);
                
                if (chunk) {
                    // Store in buffer with timestamp
                    const bufferEntry = {
                        data: chunk,
                        timestamp: Date.now(),
                        type: 'received'
                    };
                    this.serialBuffer.push(bufferEntry);
                    
                    // Log to terminal immediately for real-time display
                    if (window.serialTerminal) {
                        window.serialTerminal.logReceived(chunk);
                    }
                    
                    // Keep buffer size manageable (last 10000 entries)
                    if (this.serialBuffer.length > 10000) {
                        this.serialBuffer = this.serialBuffer.slice(-5000);
                        // Adjust consumer positions
                        this.bufferConsumers.forEach(consumer => {
                            if (consumer.position > 5000) {
                                consumer.position -= 5000;
                            } else {
                                consumer.position = 0;
                            }
                        });
                    }
                }
            } catch (error) {
                if (this.backgroundReadActive) {
                    console.error('Background read error:', error);
                    // Small delay before retrying
                    await new Promise(resolve => setTimeout(resolve, 100));
                }
            }
        }
    }

    /**
     * Create a new buffer consumer for reading data
     * @param {string} consumerId - Unique identifier for this consumer
     * @returns {object} Consumer object with methods to read data
     */
    createBufferConsumer(consumerId) {
        const consumer = {
            id: consumerId,
            position: this.serialBuffer.length, // Start from current position
            
            // Read all new data since last read
            readNew: () => {
                const newData = this.serialBuffer.slice(consumer.position);
                consumer.position = this.serialBuffer.length;
                return newData.map(entry => entry.data).join('');
            },
            
            // Read data with timeout, returns when new data arrives or timeout
            readWithTimeout: async (timeout = 200) => {
                const startTime = Date.now();
                const startPosition = consumer.position;
                
                while (Date.now() - startTime < timeout) {
                    if (consumer.position < this.serialBuffer.length) {
                        const newData = this.serialBuffer.slice(consumer.position);
                        consumer.position = this.serialBuffer.length;
                        return newData.map(entry => entry.data).join('');
                    }
                    // Small delay before checking again
                    await new Promise(resolve => setTimeout(resolve, 10));
                }
                
                return ''; // Timeout
            },
            
            // Reset position to start reading from current point
            reset: () => {
                consumer.position = this.serialBuffer.length;
            }
        };
        
        this.bufferConsumers.add(consumer);
        return consumer;
    }

    /**
     * Remove a buffer consumer
     */
    removeBufferConsumer(consumer) {
        this.bufferConsumers.delete(consumer);
    }

    /**
     * Read until we get a prompt (>>> or ...) using buffer
     */
    async readUntilPrompt() {
        if (!this.connected) {
            throw new Error('Not connected to device');
        }

        const consumer = this.createBufferConsumer('readUntilPrompt');
        let receiveMode = 0; // 0:echo, 1:data, 2:prompt
        let pending = '';
        let retryCount = 0;
        let output = '';

        try {
            while (retryCount < 3) {
                const data = await consumer.readWithTimeout(200);
                
                if (!data) {
                    retryCount++;
                    if (retryCount > 1) {
                        return null; // Return null to indicate failure
                    }
                    continue;
                }

                let processData = data;
                if (pending) {
                    processData = pending + data;
                }

                if (receiveMode === 0) {
                    const idx = processData.indexOf('\r\n');
                    if (idx < 0) {
                        pending = processData;
                        continue;
                    }
                    receiveMode = 1;
                    this.lastLineEcho = processData.substring(0, idx);
                    processData = processData.substring(idx + 2);
                    pending = '';
                    if (!processData) {
                        continue;
                    }
                }

                const stripped = processData.trim();
                if (stripped.endsWith('...') || stripped.endsWith('>>>')) {
                    receiveMode = 2;
                    processData = stripped.substring(0, stripped.length - 3);
                } else if (processData.endsWith('.') || processData.endsWith('>')) {
                    pending = processData;
                    continue;
                }

                if (pending) {
                    pending = '';
                }

                output += processData;

                if (receiveMode === 2) {
                    break;
                }
            }
        } finally {
            this.removeBufferConsumer(consumer);
        }

        return output;
    }

    /**
     * Send a line to the device and wait for prompt
     * @param {string} line - The line to send
     * @returns {string|null} - The response content, or null if failed
     */
    async sendLine(line) {
        if (!this.connected || !this.writer) {
            throw new Error('Not connected to device');
        }

        const encoder = new TextEncoder();
        const data = encoder.encode(line + '\r\n');
        const sentText = line + '\r\n';
        
        await this.writer.write(data);
        const result = await this.readUntilPrompt();
        
        return result;
    }

    /**
     * Convert binary data to hex string and wrap in MicroPython code
     */
    wrapCodeHex(binCode, saveTo = null, append = false) {
        const chunkSize = this.chunkSize;
        
        // Convert string to bytes if needed
        let bytes;
        if (typeof binCode === 'string') {
            const encoder = new TextEncoder();
            bytes = encoder.encode(binCode);
        } else {
            bytes = binCode;
        }

        // Convert to hex string
        let hexStr = '';
        for (let i = 0; i < bytes.length; i++) {
            hexStr += bytes[i].toString(16).padStart(2, '0');
        }

        let output = '';
        output += `import gc; gc.collect(); b_ = bytearray(${bytes.length}); bi_ = 0\r\n`;
        
        const chunks = Math.ceil(hexStr.length / chunkSize);
        for (let i = 0; i < chunks; i++) {
            const chunk = hexStr.substring(i * chunkSize, (i + 1) * chunkSize);
            output += `c_ = b'${chunk}'\r\n`;
            output += "for i in range(len(c_)//2): b_[bi_+i] = int(c_[2*i:2*i+2], 16).to_bytes(1, 'little')[0]\r\n";
            output += "_EMPTY_\r\n";
            output += 'bi_ += len(c_)//2; print(".", end=""); del c_; gc.collect()\r\n';
        }
        
        if (saveTo === null) {
            output += 'print(" Running."); print("--------"); b_ = b_.decode()\r\n';
            output += 'exec(b_)\r\n';
            output += 'del b_\r\n';
        } else {
            const writeMode = append ? 'ab' : 'wb';
            output += `f_ = open('${saveTo}', '${writeMode}')\r\n`;
            output += '_ = f_.write(b_)\r\n';
            output += 'f_.close();\r\n';
            output += 'del f_; del b_; gc.collect(); print(" Done.")\r\n';
        }
        
        return output;
    }

    /**
     * Execute raw code on the device
     */
    async executeCodeRaw(code, retry = false) {
        if (!this.connected) {
            throw new Error('Not connected to device');
        }

        // Send Ctrl-C to interrupt current program
        const encoder = new TextEncoder();
        const ctrlC = '\x03';
        
        await this.writer.write(encoder.encode(ctrlC));
        
        await new Promise(resolve => setTimeout(resolve, 300));
        
        await this.writer.write(encoder.encode(ctrlC));

        // Read any pending data
        const data = await this.readUntilPrompt();
        if (data === null) {
            throw new Error('Device is not responding. Try unplugging and resetting the device.');
        }

        // Send the code line by line
        const normalizedCode = code.replace(/\r/g, '\n');
        const lines = normalizedCode.split('\n');
        
        for (const line of lines) {
            const trimmedLine = line.trim();
            if (!trimmedLine) {
                continue;
            }
            
            const actualLine = trimmedLine === '_EMPTY_' ? '' : trimmedLine;
            
            if (!retry || actualLine.startsWith('exec(')) {
                if (await this.sendLine(actualLine) === null) {
                    throw new Error('Failed to send line to device');
                }
            } else {
                // Retry logic for unstable connections
                let success = false;
                for (let attempt = 0; attempt < 3; attempt++) {
                    const lineResult = await this.sendLine(actualLine);
                    if (lineResult !== null && !lineResult.includes('Traceback')) {
                        success = true;
                        break;
                    }
                }
                if (!success) {
                    throw new Error('Failed to send line after retries');
                }
            }
        }
    }

    /**
     * Download code from the device
     * @param {string} filename - Source filename to download (default: 'main.py')
     * @returns {string} - The file content as a string
     */
    async downloadCode(filename = 'main.py') {
        if (!this.connected) {
            throw new Error('Not connected to device. Call connect() first.');
        }

        try {
            console.log(`Downloading code from ${filename}...`);
            
            // Send Ctrl-C to interrupt current program
            const encoder = new TextEncoder();
            const ctrlC = '\x03';
            
            await this.writer.write(encoder.encode(ctrlC));
            
            await new Promise(resolve => setTimeout(resolve, 300));
            
            await this.writer.write(encoder.encode(ctrlC));
            
            const data = await this.readUntilPrompt();
            if (data === null) {
                throw new Error('Device is not responding. Try unplugging and resetting the device.');
            }

            // Check if file exists first
            await this.sendLine(`try: f = open('${filename}', 'r'); f.close(); print("FILE_EXISTS")`);
            await this.sendLine(`except: print("FILE_NOT_FOUND")`);
            const checkResult = await this.sendLine(``); // Empty line to execute the block
            
            if (checkResult.includes('FILE_NOT_FOUND')) {
                throw new Error(`File '${filename}' not found on device`);
            }

            // Read the file content
            await this.sendLine(`f = open('${filename}', 'r'); content = f.read(); f.close()`);
            const result = await this.sendLine(`print("===FILE_START===", end=""); print(content, end=""); print("===FILE_END===")`);
            
            // Extract content between markers
            const startMarker = '===FILE_START===';
            const endMarker = '===FILE_END===';
            const startIndex = result.indexOf(startMarker);
            const endIndex = result.indexOf(endMarker);
            
            if (startIndex === -1 || endIndex === -1) {
                throw new Error('Failed to read file content from device');
            }
            
            const content = result.substring(startIndex + startMarker.length, endIndex).replace(/\r\n/g, '\n');
            console.log(`Successfully downloaded ${filename} (${content.length} characters)`);
            
            return content;
        } catch (error) {
            console.error('Failed to download code:', error);
            throw error;
        }
    }

    /**
     * Upload code to the device
     * @param {string} code - The code to upload
     * @param {string} filename - Target filename (default: 'main.py')
     */
    async uploadCode(code, filename = 'main.py') {
        if (!this.connected) {
            throw new Error('Not connected to device. Call connect() first.');
        }

        if (code.startsWith('# filename: ')) {
            // Extract filename from code comment
            const match = code.match(/# filename:\s*(\S+)/);
            if (match && match[1]) {
                filename = match[1];
            }
        }

        try {
            console.log(`Uploading code to ${filename}...`);
            
            // Split large files into chunks
            // This has to be half of this.chunkSize to avoid OSError 28
            const chunkSize = this.chunkSize // 2;
            const chunks = Math.ceil(code.length / chunkSize);
            
            for (let i = 0; i < chunks; i++) {
                const chunk = code.substring(i * chunkSize, (i + 1) * chunkSize);
                const append = i > 0;
                
                if (append) {
                    console.log(`Uploading chunk ${i + 1}/${chunks}...`);
                }
                
                // Wrap the chunk in MicroPython upload code
                const wrappedCode = this.wrapCodeHex(chunk, filename, append);
                
                // Execute the wrapped code
                await this.executeCodeRaw(wrappedCode, true);
            }
            
            console.log(`Successfully uploaded code to ${filename}`);
            return true;
        } catch (error) {
            console.error('Failed to upload code:', error);
            throw error;
        }
    }

    /**
     * Check if connected to device
     */
    isConnected() {
        return this.connected;
    }

    /**
     * Update UI button states if the updateButtonStates function exists
     */
    updateUIButtonStates() {
        // Call the global updateButtonStates function if it exists
        if (typeof window.updateButtonStates === 'function') {
            window.updateButtonStates();
        }
    }

    /**
     * Get device info if available
     */
    getDeviceInfo() {
        if (!this.port) {
            return null;
        }
        
        const info = this.port.getInfo();
        return {
            usbVendorId: info.usbVendorId,
            usbProductId: info.usbProductId
        };
    }
}

// Create a global instance
const robot = new RobotController();

// Export the main functions
window.robotConnect = () => robot.connect();
window.robotDisconnect = () => robot.disconnect();
window.robotUploadCode = (code, filename) => robot.uploadCode(code, filename);
window.robotDownloadCode = (filename) => robot.downloadCode(filename);
window.robotIsConnected = () => robot.isConnected();
window.robotGetDeviceInfo = () => robot.getDeviceInfo();
window.robotSendRaw = async (data) => {
    if (robot.connected && robot.writer) {
        const encoder = new TextEncoder();
        const bytes = encoder.encode(data);
        
        await robot.writer.write(bytes);
    }
};

// Also export the class for advanced usage
window.RobotController = RobotController;

console.log('Robot.js loaded. Use robotConnect(), robotDisconnect(), robotUploadCode(), and robotDownloadCode() functions.');

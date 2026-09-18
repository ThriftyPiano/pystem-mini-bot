// Example Manager for handling example files
const exampleManager = {
    examples: {},
    exampleFiles: [
        'led_blink.py',
        'line_follow.py',
        'motor_control.py',
        'sdk_boot.py',
        'sdk_color_sensor.py',
        'sdk_config.py',
        'sdk_distance_sensor.py',
        'sdk_head.py',
        'sdk_motor.py',
        'sdk_motor_pair.py',
        'sdk_orientation.py',
        'sdk_speech.py',
        'sdk_wonder_echo.py',
        'voice_drive.py',
        'voice_speech.py',
    ],

    async init() {
        // Show loading message
        document.getElementById('examples-list').innerHTML = '<div class="loading-message">Loading examples...</div>';
        document.getElementById('sdk-list').innerHTML = '<div class="loading-message">Loading SDK...</div>';
        
        // Load all example files
        for (const filename of this.exampleFiles) {
            try {
                // Revalidate every load: GitHub Pages serves these with a 10-minute
                // max-age, and a stale SDK file in the IDE is confusing.
                const response = await fetch(`examples/${filename}`, {cache: 'no-cache'});
                if (response.ok) {
                    this.examples[filename] = await response.text();
                } else {
                    console.warn(`Could not load example: ${filename}`);
                }
            } catch (error) {
                console.error(`Error loading example ${filename}:`, error);
            }
        }
        
        // Populate the examples list
        this.renderExamplesList();
    },

    isSdkFile(filename) {
        return filename.startsWith('sdk_');
    },

    renderExamplesList() {
        const loaded = Object.keys(this.examples).sort();
        this.renderList('examples-list', loaded.filter(f => !this.isSdkFile(f)), 'No examples available');
        this.renderList('sdk-list', loaded.filter(f => this.isSdkFile(f)), 'No SDK files available');
    },

    renderList(elementId, filenames, emptyMessage) {
        const list = document.getElementById(elementId);
        if (filenames.length === 0) {
            list.innerHTML = `<div class="no-examples">${emptyMessage}</div>`;
            return;
        }
        list.innerHTML = '';
        filenames.forEach(filename => {
            const item = document.createElement('div');
            item.className = 'example-item';
            item.textContent = filename;
            item.onclick = () => this.loadExample(filename);
            list.appendChild(item);
        });
    },

    loadExample(filename) {
        if (!this.examples[filename]) {
            alert('Example not found: ' + filename);
            return;
        }

        if (editor) {
            // Clear the current file reference to prevent overwriting browser files
            if (fileManager) {
                fileManager.currentFile = null;
                // Re-render file list to remove active highlighting
                fileManager.renderFileList();
            }
            
            // Load content into editor (read-only mode)
            editor.setValue(this.examples[filename]);
            editor.updateOptions({ readOnly: true });
            
            // Update header to show this is an example (read-only)
            // const fileManagerHeader = document.getElementById('file-manager-header');
            // if (fileManagerHeader) {
            //     fileManagerHeader.innerHTML = 
            //         `Example: ${filename} (Read-only)
            //         <button class="new-file-btn" onclick="exampleManager.makeEditable()">Make Editable</button>`;
            // }
        } else {
            alert('Editor not ready yet. Please wait a moment and try again.');
        }
    },

    makeEditable() {
        if (editor) {
            editor.updateOptions({ readOnly: false });
            
            // Re-render file list to clear any active file highlighting
            if (fileManager) {
                fileManager.renderFileList();
            }
            
            // Reset header to normal file browser
            const fileManagerHeader = document.getElementById('file-manager-header');
            if (fileManagerHeader) {
                fileManagerHeader.innerHTML = 
                    `Files in browser
                    <button class="new-file-btn" id="new-file-btn">+ New</button>`;
                
                // Re-attach event listener to new button
                document.getElementById('new-file-btn').onclick = () => fileManager.newFile();
            }
        }
    }
};

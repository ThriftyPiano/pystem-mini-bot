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
        'sdk_motor.py',
        'sdk_motor_pair.py',
        'sdk_orientation.py',
    ],

    async init() {
        // Show loading message
        const examplesList = document.getElementById('examples-list');
        examplesList.innerHTML = '<div class="loading-message">Loading examples...</div>';
        
        // Load all example files
        for (const filename of this.exampleFiles) {
            try {
                const response = await fetch(`examples/${filename}`);
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

    renderExamplesList() {
        const examplesList = document.getElementById('examples-list');
        const loadedExamples = Object.keys(this.examples);
        
        if (loadedExamples.length === 0) {
            examplesList.innerHTML = '<div class="no-examples">No examples available</div>';
            return;
        }
        
        examplesList.innerHTML = '';
        loadedExamples.sort().forEach(filename => {
            const exampleItem = document.createElement('div');
            exampleItem.className = 'example-item';
            exampleItem.textContent = filename;
            exampleItem.onclick = () => this.loadExample(filename);
            examplesList.appendChild(exampleItem);
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

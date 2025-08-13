// File management system using localStorage
class FileManager {
    constructor() {
        this.currentFile = null;
        this.editor = null;
        this.files = this.loadFiles();
        this.init();
    }

    init() {
        this.renderFileList();
        this.setupEventListeners();        
    }

    loadFiles() {
        const stored = localStorage.getItem('esp32-robot-files');
        return stored ? JSON.parse(stored) : {};
    }

    saveFiles() {
        localStorage.setItem('esp32-robot-files', JSON.stringify(this.files));
    }

    createFile(name, content = '') {
        if (!name || this.files[name]) return false;
        
        this.files[name] = {
            content: content,
            lastModified: Date.now()
        };
        this.saveFiles();
        this.renderFileList();
        this.openFile(name);
        return true;
    }

    deleteFile(name) {
        if (!this.files[name]) return false;
        
        delete this.files[name];
        this.saveFiles();
        
        // Clear current file reference if it's the deleted file
        if (this.currentFile === name) {
            this.currentFile = null;
        }
        
        this.renderFileList();
        
        // Open another file if any exist
        const fileNames = Object.keys(this.files);
        if (fileNames.length > 0) {
            this.openFile(fileNames[0]);
        } else {
            if (this.editor) {
                this.editor.setValue('');
            }
        }
        
        return true;
    }

    renameFile(oldName, newName) {
        if (!this.files[oldName] || !newName || this.files[newName]) return false;
        
        this.files[newName] = this.files[oldName];
        delete this.files[oldName];
        this.saveFiles();
        this.renderFileList();
        
        if (this.currentFile === oldName) {
            this.currentFile = newName;
        }
        return true;
    }

    openFile(name) {
        if (!this.files[name]) return false;
        
        // Save current file before switching
        if (this.currentFile && this.editor) {
            this.files[this.currentFile].content = this.editor.getValue();
            this.saveFiles();
        }
        
        this.currentFile = name;
        if (this.editor) {
            this.editor.setValue(this.files[name].content);
            // Ensure editor is editable when opening browser files
            this.editor.updateOptions({ readOnly: false });
        }
        this.renderFileList();
        return true;
    }

    getCurrentFileContent() {
        if (this.currentFile && this.editor) {
            return this.editor.getValue();
        }
        return '';
    }

    getCurrentFileName() {
        return this.currentFile;
    }

    saveCurrentFile() {
        if (this.currentFile && this.editor) {
            this.files[this.currentFile].content = this.editor.getValue();
            this.files[this.currentFile].lastModified = Date.now();
            this.saveFiles();
        }
    }

    renderFileList() {
        const fileList = document.getElementById('file-list');
        fileList.innerHTML = '';
        
        Object.keys(this.files).sort().forEach(fileName => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            if (fileName === this.currentFile) {
                fileItem.classList.add('active');
            }
            
            fileItem.innerHTML = `
                <span class="file-name">${fileName}</span>
                <div class="file-actions">
                    <button class="file-action-btn" onclick="fileManager.promptRename('${fileName}')">↻</button>
                    <button class="file-action-btn" onclick="fileManager.confirmDelete('${fileName}')">×</button>
                </div>
            `;
            
            fileItem.addEventListener('click', (e) => {
                if (!e.target.classList.contains('file-action-btn')) {
                    this.openFile(fileName);
                }
            });
            
            fileList.appendChild(fileItem);
        });
    }

    setupEventListeners() {
        document.getElementById('new-file-btn').addEventListener('click', () => {
            this.promptNewFile();
        });
        
        // Auto-save on editor change
        setInterval(() => {
            if (this.currentFile && this.editor) {
                this.saveCurrentFile();
            }
        }, 2000); // Auto-save every 2 seconds
    }

    promptNewFile() {
        const name = prompt('Enter file name (e.g., servo_control.py):');
        if (name) {
            if (this.createFile(name)) {
                console.log(`Created file: ${name}`);
            } else {
                alert('File already exists or invalid name!');
            }
        }
    }

    promptRename(oldName) {
        const newName = prompt(`Rename "${oldName}" to:`, oldName);
        if (newName && newName !== oldName) {
            if (this.renameFile(oldName, newName)) {
                console.log(`Renamed "${oldName}" to "${newName}"`);
            } else {
                alert('File already exists or invalid name!');
            }
        }
    }

    confirmDelete(name) {
        if (confirm(`Delete "${name}"?`)) {
            if (this.deleteFile(name)) {
                console.log(`Deleted file: ${name}`);
            }
        }
    }

    setEditor(editor) {
        this.editor = editor;
        // Load the first file or current file
        const fileNames = Object.keys(this.files);
        if (fileNames.length > 0) {
            this.openFile(this.currentFile || fileNames[0]);
        } else {
            this.createFile('hello_world.py', `# Basic LED Blink Example
from machine import Pin
import time

# Configure the built-in LED (usually pin 2 on ESP32)
led = Pin(2, Pin.OUT)

print("Starting LED blink example...")

# Blink the LED forever
while True:
    led.on()
    print("LED ON")
    time.sleep(1)
    
    led.off()
    print("LED OFF")
    time.sleep(1)
`);
        }
    }
}

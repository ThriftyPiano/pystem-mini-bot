// Monaco Editor MicroPython Auto-completion Setup
class MonacoMicroPythonSetup {
    constructor() {
        this.stubDefinitions = new Map();
        this.isSetupComplete = false;
    }

    async loadStubFiles() {
        const stubFiles = [
            'machine.pyi',
            'time.pyi', 
            'esp32.pyi',
            'network.pyi',
            'math.pyi'
        ];

        const loadPromises = stubFiles.map(async (fileName) => {
            try {
                const response = await fetch(`stubs/${fileName}`);
                if (response.ok) {
                    const content = await response.text();
                    this.stubDefinitions.set(fileName.replace('.pyi', ''), content);
                    console.log(`Loaded stub: ${fileName}`);
                } else {
                    console.warn(`Failed to load stub: ${fileName}`);
                }
            } catch (error) {
                console.error(`Error loading ${fileName}:`, error);
            }
        });

        await Promise.all(loadPromises);
    }

    parseStubContent(stubContent, moduleName) {
        const completionItems = [];
        const lines = stubContent.split('\n');
        
        let currentClass = null;
        let currentIndent = 0;
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const trimmedLine = line.trim();
            
            // Skip empty lines and comments
            if (!trimmedLine || trimmedLine.startsWith('#')) continue;
            
            const indent = line.length - line.trimLeft().length;
            
            // Class definitions
            if (trimmedLine.startsWith('class ')) {
                const classMatch = trimmedLine.match(/class\s+(\w+)/);
                if (classMatch) {
                    currentClass = classMatch[1];
                    currentIndent = indent;
                    
                    completionItems.push({
                        label: currentClass,
                        kind: monaco.languages.CompletionItemKind.Class,
                        insertText: currentClass,
                        detail: `class ${currentClass}`,
                        documentation: this.extractDocstring(lines, i + 1)
                    });
                }
            }
            
            // Function/method definitions
            else if (trimmedLine.startsWith('def ')) {
                const funcMatch = trimmedLine.match(/def\s+(\w+)\s*\(([^)]*)\)/);
                if (funcMatch) {
                    const funcName = funcMatch[1];
                    const params = funcMatch[2];
                    
                    // Skip magic methods for now
                    if (funcName.startsWith('__')) continue;
                    
                    let insertText = funcName;
                    let label = funcName;
                    
                    // Parse parameters
                    if (params && params.trim()) {
                        const paramList = params.split(',').map(p => {
                            const param = p.trim();
                            // Remove type hints and default values for display
                            const cleanParam = param.split(':')[0].split('=')[0].trim();
                            return cleanParam;
                        }).filter(p => p && p !== 'self');
                        
                        if (paramList.length > 0) {
                            const paramString = paramList.map((p, idx) => `\${${idx + 1}:${p}}`).join(', ');
                            insertText = `${funcName}(${paramString})`;
                            label = `${funcName}(${paramList.join(', ')})`;
                        } else {
                            insertText = `${funcName}()`;
                            label = `${funcName}()`;
                        }
                    } else {
                        insertText = `${funcName}()`;
                        label = `${funcName}()`;
                    }
                    
                    const isMethod = currentClass && indent > currentIndent;
                    
                    completionItems.push({
                        label: label,
                        kind: monaco.languages.CompletionItemKind.Function,
                        insertText: insertText,
                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                        detail: isMethod ? `method of ${currentClass}` : `function in ${moduleName}`,
                        documentation: this.extractDocstring(lines, i + 1),
                        filterText: funcName,
                        sortText: funcName
                    });
                }
            }
            
            // Constants and variables
            else if (trimmedLine.includes(' = ') && !trimmedLine.startsWith('def ') && !trimmedLine.startsWith('class ')) {
                const varMatch = trimmedLine.match(/^(\w+)\s*[:=]/);
                if (varMatch) {
                    const varName = varMatch[1];
                    
                    completionItems.push({
                        label: varName,
                        kind: monaco.languages.CompletionItemKind.Variable,
                        insertText: varName,
                        detail: `constant in ${moduleName}`,
                        documentation: `${moduleName}.${varName}`
                    });
                }
            }
            
            // Reset class context when exiting class
            if (currentClass && indent <= currentIndent && trimmedLine) {
                currentClass = null;
                currentIndent = 0;
            }
        }
        
        return completionItems;
    }

    parseClassMethods(stubContent, className) {
        const methods = [];
        const lines = stubContent.split('\n');
        let insideClass = false;
        let classIndent = 0;
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const trimmedLine = line.trim();
            const indent = line.length - line.trimLeft().length;
            
            // Check if we're entering the target class
            if (trimmedLine.startsWith(`class ${className}`)) {
                insideClass = true;
                classIndent = indent;
                continue;
            }
            
            // Check if we've left the class
            if (insideClass && indent <= classIndent && trimmedLine && !trimmedLine.startsWith('#')) {
                insideClass = false;
                continue;
            }
            
            // If we're inside the class, look for method definitions
            if (insideClass && trimmedLine.startsWith('def ')) {
                const funcMatch = trimmedLine.match(/def\s+(\w+)\s*\(([^)]*)\)/);
                if (funcMatch) {
                    const funcName = funcMatch[1];
                    const params = funcMatch[2];
                    
                    // Skip magic methods except common ones
                    if (funcName.startsWith('__') && !['__init__', '__call__'].includes(funcName)) {
                        continue;
                    }
                    
                    let insertText = funcName;
                    let label = funcName;
                    
                    // Parse parameters (skip 'self')
                    if (params && params.trim()) {
                        const paramList = params.split(',').map(p => {
                            const param = p.trim();
                            const cleanParam = param.split(':')[0].split('=')[0].trim();
                            return cleanParam;
                        }).filter(p => p && p !== 'self');
                        
                        if (paramList.length > 0) {
                            const paramString = paramList.map((p, idx) => `\${${idx + 1}:${p}}`).join(', ');
                            insertText = `${funcName}(${paramString})`;
                            label = `${funcName}(${paramList.join(', ')})`;
                        } else {
                            insertText = `${funcName}()`;
                            label = `${funcName}()`;
                        }
                    } else {
                        insertText = `${funcName}()`;
                        label = `${funcName}()`;
                    }
                    
                    methods.push({
                        label: label,
                        kind: monaco.languages.CompletionItemKind.Method,
                        insertText: insertText,
                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                        detail: `method of ${className}`,
                        documentation: this.extractDocstring(lines, i + 1),
                        filterText: funcName,
                        sortText: funcName
                    });
                }
            }
        }
        
        return methods;
    }

    parseClassAttributes(stubContent, className) {
        const attributes = [];
        const lines = stubContent.split('\n');
        let insideClass = false;
        let classIndent = 0;
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const trimmedLine = line.trim();
            const indent = line.length - line.trimLeft().length;
            
            // Check if we're entering the target class
            if (trimmedLine.startsWith(`class ${className}`)) {
                insideClass = true;
                classIndent = indent;
                continue;
            }
            
            // Check if we've left the class
            if (insideClass && indent <= classIndent && trimmedLine && !trimmedLine.startsWith('#')) {
                insideClass = false;
                continue;
            }
            
            // If we're inside the class, look for class attributes (constants)
            if (insideClass && trimmedLine.includes(' = ') && !trimmedLine.startsWith('def ')) {
                const attrMatch = trimmedLine.match(/^(\w+)\s*=\s*(.+)/);
                if (attrMatch) {
                    const attrName = attrMatch[1];
                    const attrValue = attrMatch[2];
                    
                    attributes.push({
                        label: attrName,
                        kind: monaco.languages.CompletionItemKind.Constant,
                        insertText: attrName,
                        detail: `${className}.${attrName} = ${attrValue}`,
                        documentation: `Class constant of ${className}`,
                        sortText: attrName
                    });
                }
            }
        }
        
        return attributes;
    }

    extractDocstring(lines, startIndex) {
        if (startIndex >= lines.length) return '';
        
        const nextLine = lines[startIndex]?.trim();
        if (nextLine?.startsWith('"""') || nextLine?.startsWith("'''")) {
            // Multi-line docstring
            const quote = nextLine.substring(0, 3);
            let docstring = nextLine.substring(3);
            
            if (docstring.endsWith(quote)) {
                return docstring.substring(0, docstring.length - 3);
            }
            
            for (let i = startIndex + 1; i < lines.length; i++) {
                const line = lines[i];
                if (line.includes(quote)) {
                    docstring += '\n' + line.substring(0, line.indexOf(quote));
                    break;
                }
                docstring += '\n' + line;
            }
            return docstring.trim();
        }
        return '';
    }

    setupMonacoCompletions() {
        if (!monaco || !monaco.languages) {
            console.error('Monaco editor not ready');
            return;
        }

        // Register completion provider for Python
        monaco.languages.registerCompletionItemProvider('python', {
            provideCompletionItems: (model, position) => {
                const textUntilPosition = model.getValueInRange({
                    startLineNumber: 1,
                    startColumn: 1,
                    endLineNumber: position.lineNumber,
                    endColumn: position.column
                });

                const word = model.getWordUntilPosition(position);
                const range = {
                    startLineNumber: position.lineNumber,
                    endLineNumber: position.lineNumber,
                    startColumn: word.startColumn,
                    endColumn: word.endColumn
                };

                const suggestions = [];

                // Check if we're after "from " or "import "
                const importMatch = textUntilPosition.match(/(?:from\s+|import\s+)(\w*)$/);
                if (importMatch) {
                    // Suggest module names
                    for (const [moduleName] of this.stubDefinitions) {
                        suggestions.push({
                            label: moduleName,
                            kind: monaco.languages.CompletionItemKind.Module,
                            insertText: moduleName,
                            range: range,
                            detail: `MicroPython module`,
                            documentation: `Import ${moduleName} module for MicroPython`
                        });
                    }
                    return { suggestions };
                }

                // Check if we're accessing something with dot notation
                const dotAccessMatch = textUntilPosition.match(/(\w+)\.(\w*)$/);
                if (dotAccessMatch) {
                    const leftSide = dotAccessMatch[1];
                    
                    // First, check if it's a known module
                    const stubContent = this.stubDefinitions.get(leftSide);
                    if (stubContent) {
                        const moduleCompletions = this.parseStubContent(stubContent, leftSide);
                        suggestions.push(...moduleCompletions.map(item => ({
                            ...item,
                            range: range
                        })));
                        return { suggestions };
                    }
                    
                    // Second, check if it's a class name (look for class in any stub file)
                    for (const [moduleName, stubContent] of this.stubDefinitions) {
                        if (stubContent.includes(`class ${leftSide}`)) {
                            const classAttributes = this.parseClassAttributes(stubContent, leftSide);
                            if (classAttributes.length > 0) {
                                suggestions.push(...classAttributes.map(item => ({
                                    ...item,
                                    range: range
                                })));
                                return { suggestions };
                            }
                        }
                    }
                    
                    // Third, check if it's an object instance (variable assignment)
                    // Try to find what type this object might be from previous lines
                    const allText = model.getValue();
                    const lines = allText.split('\n').slice(0, position.lineNumber - 1);
                    
                    console.log(`Looking for object type of "${leftSide}"`);
                    
                    for (const line of lines) {
                        // Look for various variable assignment patterns:
                        // led = Pin(...)
                        // led = machine.Pin(...)
                        // self.led = Pin(...)
                        const patterns = [
                            new RegExp(`${leftSide}\\s*=\\s*(?:(\\w+)\\.)??(\\w+)\\s*\\(`),
                            new RegExp(`self\\.${leftSide}\\s*=\\s*(?:(\\w+)\\.)??(\\w+)\\s*\\(`),
                            new RegExp(`\\w+\\.${leftSide}\\s*=\\s*(?:(\\w+)\\.)??(\\w+)\\s*\\(`)
                        ];
                        
                        for (const pattern of patterns) {
                            const assignmentMatch = line.match(pattern);
                            if (assignmentMatch) {
                                const moduleName = assignmentMatch[1];
                                const className = assignmentMatch[2];
                                
                                console.log(`Found ${leftSide} = ${moduleName ? moduleName + '.' : ''}${className}(...)`);
                                
                                // Find the stub content for the class
                                for (const [stubModuleName, stubContent] of this.stubDefinitions) {
                                    if (stubContent.includes(`class ${className}`)) {
                                        console.log(`Found class ${className} in ${stubModuleName} module`);
                                        const classCompletions = this.parseClassMethods(stubContent, className);
                                        console.log(`Generated ${classCompletions.length} completions for ${className}`);
                                        suggestions.push(...classCompletions.map(item => ({
                                            ...item,
                                            range: range
                                        })));
                                        return { suggestions };
                                    }
                                }
                                break; // Found a match, no need to check other patterns
                            }
                        }
                    }
                }

                // Add modules
                for (const [moduleName] of this.stubDefinitions) {
                    suggestions.push({
                        label: moduleName,
                        kind: monaco.languages.CompletionItemKind.Module,
                        insertText: moduleName,
                        range: range,
                        detail: `MicroPython module`,
                        documentation: `MicroPython ${moduleName} module`,
                        sortText: `0${moduleName}` // Higher priority
                    });
                }

                // Parse local variables from the current file
                const allText = model.getValue();
                const lines = allText.split('\n');
                const localVariables = new Set();
                
                // Look for variable assignments in the current file
                for (const line of lines) {
                    // Match variable assignments: var = something
                    const varMatch = line.match(/^\s*(\w+)\s*=/);
                    if (varMatch && !['def', 'class', 'if', 'elif', 'else', 'for', 'while', 'try', 'except', 'finally', 'with'].includes(varMatch[1])) {
                        localVariables.add(varMatch[1]);
                    }
                    
                    // Match for loop variables: for var in something
                    const forMatch = line.match(/for\s+(\w+)\s+in/);
                    if (forMatch) {
                        localVariables.add(forMatch[1]);
                    }
                    
                    // Match function parameters: def func(param1, param2):
                    const funcMatch = line.match(/def\s+\w+\s*\(([^)]*)\)/);
                    if (funcMatch && funcMatch[1]) {
                        const params = funcMatch[1].split(',');
                        for (const param of params) {
                            const paramName = param.trim().split(':')[0].split('=')[0].trim();
                            if (paramName && paramName !== 'self') {
                                localVariables.add(paramName);
                            }
                        }
                    }
                }
                
                // Add local variables to suggestions
                for (const varName of localVariables) {
                    suggestions.push({
                        label: varName,
                        kind: monaco.languages.CompletionItemKind.Variable,
                        insertText: varName,
                        range: range,
                        detail: 'Local variable',
                        sortText: `0${varName}` // High priority for local variables
                    });
                }

                return { suggestions };
            }
        });

        // Register hover provider for better documentation
        monaco.languages.registerHoverProvider('python', {
            provideHover: (model, position) => {
                const word = model.getWordAtPosition(position);
                if (!word) return null;

                const lineContent = model.getLineContent(position.lineNumber);
                const moduleMatch = lineContent.match(/(\w+)\.(\w+)/);
                
                if (moduleMatch) {
                    const moduleName = moduleMatch[1];
                    const memberName = moduleMatch[2];
                    const stubContent = this.stubDefinitions.get(moduleName);
                    
                    if (stubContent) {
                        // Find documentation for the specific member
                        const lines = stubContent.split('\n');
                        for (let i = 0; i < lines.length; i++) {
                            if (lines[i].includes(`def ${memberName}`) || lines[i].includes(`class ${memberName}`)) {
                                const docstring = this.extractDocstring(lines, i + 1);
                                if (docstring) {
                                    return {
                                        range: new monaco.Range(
                                            position.lineNumber,
                                            word.startColumn,
                                            position.lineNumber,
                                            word.endColumn
                                        ),
                                        contents: [
                                            { value: `**${moduleName}.${memberName}**` },
                                            { value: docstring }
                                        ]
                                    };
                                }
                            }
                        }
                    }
                }

                return null;
            }
        });

        console.log('Monaco MicroPython completions setup complete');
        this.isSetupComplete = true;
    }

    async initialize() {
        try {
            console.log('Loading MicroPython stub files...');
            await this.loadStubFiles();
            
            console.log(`Loaded ${this.stubDefinitions.size} stub files`);
            
            // Wait for Monaco to be ready if not already
            if (typeof monaco !== 'undefined') {
                this.setupMonacoCompletions();
            } else {
                // Wait for Monaco to load
                const checkMonaco = () => {
                    if (typeof monaco !== 'undefined') {
                        this.setupMonacoCompletions();
                    } else {
                        setTimeout(checkMonaco, 100);
                    }
                };
                checkMonaco();
            }
            
        } catch (error) {
            console.error('Failed to initialize MicroPython completions:', error);
        }
    }
}

// Export for global use
window.MonacoMicroPythonSetup = MonacoMicroPythonSetup;

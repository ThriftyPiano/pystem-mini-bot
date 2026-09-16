// Speech model sessions shared by the pages that consume what the
// trainer (speech-commands.html) stores in localStorage (same origin):
//   speech-sessions        {active, sessions:[{id, name, ...}]}
//   speech-model:<id>      {labels, data (base64 quantized classifier), ...}
// SpeechModels.toPython() renders the on-device speech_model.py from a
// stored payload. The "# filename:" header is what the IDE's upload uses
// to name the file on the robot; without it the code would land in main.py.
window.SpeechModels = {
    sessions() {
        try {
            const idx = JSON.parse(localStorage.getItem('speech-sessions')) || {sessions: []};
            return idx.sessions.filter(s => localStorage.getItem('speech-model:' + s.id));
        } catch (e) { return []; }
    },
    payload(id) {
        try { return JSON.parse(localStorage.getItem('speech-model:' + id)); }
        catch (e) { return null; }
    },
    toPython(payload) {
        return `# filename: speech_model.py
import speech_commands as sp
from ubinascii import a2b_base64, b2a_base64

data = a2b_base64('${payload.data}')
sp.init(data)
labels = ${JSON.stringify(payload.labels)}
feature = bytearray(732)

def predict(audio):
    result = sp.predict(audio, 0, 0)
    return (labels[result // 1000], result % 1000)

def snapshot():
    global feature
    sp.export_mfcc(feature)

def save(label):
    with open('samples.txt', 'ab') as f:
        f.write(b'{"label": "')
        f.write(label.encode())
        f.write(b'", "mfcc": "')
        f.write(b2a_base64(feature)[:-1])
        f.write(b'"},\\n')
`;
    }
};

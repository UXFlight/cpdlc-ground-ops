const speechConfig = {
    lang: 'en-US',
    pitch: 1,
    rate: 0.92,
    volume: 1,
    voiceName: "English (America)+Michael",
};

const preferredVoices = [
    speechConfig.voiceName,
    "English (America)+Michael",
    "English (America)+Paul",
    "English (America)+Zac",
    "English (America)+Caleb",
    "English (America)+Mike",
    "English (America)+David"
];

let voice = null;
let queue = [];
let isSpeaking = false;

function loadVoices() {
    return new Promise((resolve) => {
        const synth = window.speechSynthesis;
        const voices = synth.getVoices();

        if (voices.length) {
            resolve(voices);
        } else {
            synth.onvoiceschanged = () => resolve(synth.getVoices());
        }
    });
}

export async function initVoice() {
    const voices = await loadVoices();

    for (const name of preferredVoices) {
        if (!name) continue;
        const found = voices.find(v => v.name === name);
        if (found) {
            voice = found;
            return;
        }
    }

    voice = voices.find(v => v.lang === speechConfig.lang) || voices[0];
    console.warn("⚠️ Using fallback voice:", voice?.name || "None");
}

export function speak(text) {
    if (!window.speechSynthesis || !voice) {
        console.warn("Speech synthesis not ready or voice not initialized.");
        return;
    }

    queue.push(text);
    processQueue();
}

function processQueue() {
    if (isSpeaking || queue.length === 0) return;

    const text = queue.shift();
    const utterance = new SpeechSynthesisUtterance(text);

    utterance.voice = voice;
    utterance.lang = speechConfig.lang;
    utterance.pitch = speechConfig.pitch;
    utterance.rate = speechConfig.rate;
    utterance.volume = speechConfig.volume;

    isSpeaking = true;
    utterance.onend = () => {
        isSpeaking = false;
        processQueue();
    };

    window.speechSynthesis.speak(utterance);
}

export { speechConfig };

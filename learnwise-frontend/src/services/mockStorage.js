export function readMock(key, fallback) {
    try {
        const raw = window.localStorage.getItem(`learnwise:${key}`);
        return raw ? JSON.parse(raw) : fallback;
    }
    catch {
        return fallback;
    }
}
export function writeMock(key, value) {
    window.localStorage.setItem(`learnwise:${key}`, JSON.stringify(value));
    return value;
}
export function removeMock(key) { window.localStorage.removeItem(`learnwise:${key}`); }

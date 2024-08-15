export function saveSet(key, setObject) {
    try {
        const setToArray = Array.from(setObject);
        const json = JSON.stringify(setToArray);
        sessionStorage.setItem(key, json);
    } catch (err) {
        console.warn("Error saving set to cache.", key, err);
        sessionStorage.removeItem(key);
    }
}

export function loadSet(key) {
    try {
        const arrJson = sessionStorage.getItem(key);
        const cachedArray = arrJson ? JSON.parse(arrJson) : null;
        return Array.isArray(cachedArray) ? new Set(cachedArray) : new Set();
    } catch (err) {
        console.warn("Error loading cached list.", key, err);
        sessionStorage.removeItem(key);
        return new Set();
    }
}

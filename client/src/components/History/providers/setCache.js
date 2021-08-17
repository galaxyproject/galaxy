// Caches expanded/selected Sets in sessionStorage
// Putting this in separate file for ease of mocking

export function saveSet(key, setObject) {
    try {
        const setToArray = Array.from(setObject);
        const json = JSON.stringify(setToArray);
        sessionStorage.setItem(key, json);
    } catch (err) {
        console.log("error saving stuff to cache", err);
        sessionStorage.removeItem(key);
    }
}

export function loadSet(key) {
    try {
        const arrJson = sessionStorage.getItem(key) || [];
        const cachedArray = JSON.parse(arrJson);
        return Array.isArray(cachedArray) ? new Set(cachedArray) : new Set();
    } catch (err) {
        console.log("erorr loading cached list", err);
        sessionStorage.removeItem(key);
        return null;
    }
}

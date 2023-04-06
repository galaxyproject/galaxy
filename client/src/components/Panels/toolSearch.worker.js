import { searchToolsByKeys } from "./utilities";

// listen for messages from the main thread
self.addEventListener("message", (event) => {
    const { type, payload } = event.data;
    if (type === "searchToolsByKeys") {
        const { tools, keys, query } = payload;
        const result = searchToolsByKeys(tools, keys, query);
        // send the result back to the main thread
        self.postMessage({ type: "searchToolsByKeysResult", payload: result, query: query });
    }
});

// TODO: add error event listener
// self.addEventListener('error', (event) => {

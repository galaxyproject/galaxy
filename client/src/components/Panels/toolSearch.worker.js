/**
 * A Web Worker that isolates the Tool Search into its own thread
 */

import { searchTools } from "./utilities";

// listen for messages from the main thread
self.addEventListener("message", (event) => {
    const { type, payload } = event.data;
    if (type === "searchTools") {
        const { tools, query, currentPanel } = payload;
        const { results, resultPanel, closestTerm } = searchTools(tools, query, currentPanel);
        // send the result back to the main thread
        self.postMessage({
            type: "searchToolsByKeysResult",
            payload: results,
            sectioned: resultPanel,
            query: query,
            closestTerm: closestTerm,
        });
    } else if (type === "clearFilter") {
        self.postMessage({ type: "clearFilterResult" });
    } else if (type === "favoriteTools") {
        self.postMessage({ type: "favoriteToolsResult" });
    }
});

// TODO: add error event listener
// self.addEventListener('error', (event) => {

onmessage = function(event) {
    importScripts("numeric-column-stats.js");
    postMessage(numericColumnStats(event.data.data, event.data.keys));
    self.close();
};

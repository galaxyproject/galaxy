import { runFilter } from "@/composables/filter/filterFunction";

let array = [];
let filter = "";
let fields = [];

self.addEventListener("message", (e) => {
    const message = e.data;

    if (message.type === "setArray") {
        array = message.array;
    } else if (message.type === "setFields") {
        fields = message.fields;
    } else if (message.type === "setFilter") {
        filter = message.filter;
    }

    const filtered = runFilter(filter, array, fields);
    self.postMessage({ type: "result", filtered, seq: message.seq });
});

import { buildSearchIndex, rankSearchIndex } from "@/composables/filter/filterFunction";

let array = [];
let filter = "";
let fields = [];
let index = [];

self.addEventListener("message", (e) => {
    const message = e.data;

    if (message.type === "setArray") {
        array = message.array;
        index = buildSearchIndex(array, fields);
    } else if (message.type === "setFields") {
        fields = message.fields;
        index = buildSearchIndex(array, fields);
    } else if (message.type === "setFilter") {
        filter = message.filter;
    }

    if (array.length > 0 && fields.length > 0) {
        const filtered = rankSearchIndex(index, filter);
        self.postMessage({ type: "result", filtered });
    }
});

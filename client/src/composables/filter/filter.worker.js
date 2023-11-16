import { runFilter } from "@/composables/filter/filterFunction";

let array = [];
let filter = "";
let fields = [];
let asRegex = false;

self.addEventListener("message", (e) => {
    const message = e.data;

    if (message.type === "setArray") {
        array = message.array;
    } else if (message.type === "setFields") {
        fields = message.fields;
    } else if (message.type === "setFilter") {
        filter = message.filter;
    } else if (message.type === "setAsRegex") {
        asRegex = message.asRegex;
    }

    if (array.length > 0 && fields.length > 0) {
        const filtered = runFilter(filter, array, fields, asRegex);
        self.postMessage({ type: "result", filtered });
    }
});

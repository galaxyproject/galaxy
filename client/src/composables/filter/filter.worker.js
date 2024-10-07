import { runFilter } from "@/composables/filter/filterFunction";

function createOptions() {
    return {
        array: [],
        filter: "",
        fields: [],
    };
}

const optionsById = new Map();
const timerById = new Map();

self.addEventListener("message", (e) => {
    const message = e.data;

    if (!optionsById.has(message.id)) {
        optionsById.set(message.id, createOptions());
    }

    const options = optionsById.get(message.id);

    switch (message.type) {
        case "setArray":
            options.array = message.array;
            break;

        case "setFields":
            options.fields = message.fields;
            break;

        case "setFilter":
            options.filter = message.filter;
            break;

        case "clear":
            optionsById.delete(message.id);
            break;

        default:
            break;
    }

    if (timerById.has(message.id)) {
        clearTimeout(timerById.get(message.id));
    }

    timerById.set(
        message.id,
        setTimeout(() => {
            if (options.array.length > 0 && options.fields.length > 0) {
                const filtered = runFilter(options.filter, options.array, options.fields);
                self.postMessage({ type: "result", filtered });
            }

            timerById.delete(message.id);
        }, 10)
    );
});

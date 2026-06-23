import { main } from "./selectManyMain";

// glue code to run `main` in a thread

const createOptions = () => {
    return {
        optionsArray: [],
        filter: "",
        selected: [],
        unselectedDisplayCount: 1000,
        selectedDisplayCount: 1000,
        caseSensitive: false,
        maintainSelectionOrder: false,
    };
};

const optionsById = new Map();
const timerById = {};

self.addEventListener("message", (e) => {
    const message = e.data;

    if (!optionsById.has(message.id)) {
        optionsById.set(message.id, createOptions());
    }

    const options = optionsById.get(message.id);

    switch (message.type) {
        case "setArray":
            options.optionsArray = message.array;
            break;

        case "setFilter":
            options.filter = message.filter;
            break;

        case "setSelected":
            options.selected = message.selected;
            break;

        case "setSettings":
            options.unselectedDisplayCount = message.unselectedDisplayCount;
            options.selectedDisplayCount = message.selectedDisplayCount;
            options.caseSensitive = message.caseSensitive;
            options.maintainSelectionOrder = message.maintainSelectionOrder;
            break;

        case "clear":
            optionsById.delete(message.id);
            return;

        default:
            break;
    }

    if (message.id in timerById) {
        clearTimeout(timerById[message.id]);
    }

    timerById[message.id] = setTimeout(() => {
        const result = main(options);
        self.postMessage({ id: message.id, type: "result", ...result });
    }, 10);
});

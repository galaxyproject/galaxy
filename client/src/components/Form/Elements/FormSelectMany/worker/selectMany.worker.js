import { main } from "./selectManyMain";

// glue code to run `main` in a thread

const createOptions = () => ({
    optionsArray: [],
    filter: "",
    selected: [],
    unselectedDisplayCount: 1000,
    selectedDisplayCount: 1000,
    asRegex: false,
    caseSensitive: false,
});

const optionsById = {};
const timerById = {};

self.addEventListener("message", (e) => {
    const message = e.data;

    if (!(message.id in optionsById)) {
        optionsById[message.id] = createOptions();
    }

    const options = optionsById[message.id];

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

        case "setSetting":
            options.unselectedDisplayCount = message.unselectedDisplayCount;
            options.selectedDisplayCount = message.selectedDisplayCount;
            options.asRegex = message.asRegex;
            options.caseSensitive = message.caseSensitive;
            break;

        case "clear":
            delete optionsById[message.id];
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

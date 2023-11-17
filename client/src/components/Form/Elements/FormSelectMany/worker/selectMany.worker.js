import { main } from "./selectManyMain";

// glue code to run `main` in a thread

const options = {
    optionsArray: [],
    filter: [],
    unselected: [],
    selected: [],
    unselectedDisplayCount: 1000,
    selectedDisplayCount: 1000,
    asRegex: false,
    caseSensitive: false,
};

let timer;

self.addEventListener("message", (e) => {
    const message = e.data;

    switch (message.type) {
        case "setArray":
            options.optionsArray = message.array;
            break;

        case "setFilter":
            options.filter = message.filter;
            break;

        case "setUnselected":
            options.unselected = message.unselected;
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

        default:
            break;
    }

    clearTimeout(timer);
    timer = setTimeout(() => {
        const result = main(options);
        self.postMessage({ type: "result", ...result });
    }, 10);
});

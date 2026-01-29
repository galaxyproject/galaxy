// bootstrap vue will try to match targets to actual HTML elements in DOM but there
// may be no DOM for jest tests, just stub out an alternative minimal implementation.
jest.mock("@/components/Help/HelpPopover.vue", () => ({
    name: "HelpPopover",
    render: (h) => h("div", "Mocked Popover"),
}));

jest.mock("@/components/ObjectStore/ObjectStoreSelectButtonPopover.vue", () => ({
    name: "ObjectStoreSelectButtonPopover",
    render: (h) => h("div", "Mocked Popover"),
}));

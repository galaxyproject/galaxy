import { vi } from "vitest";

// bootstrap vue will try to match targets to actual HTML elements in DOM but there
// may be no DOM for vitest tests, just stub out an alternative minimal implementation.
vi.mock("@/components/Help/HelpPopover.vue", () => ({
    name: "HelpPopover",
    render: (h) => h("div", "Mocked Popover"),
}));

vi.mock("@/components/ObjectStore/ObjectStoreSelectButtonPopover.vue", () => ({
    name: "ObjectStoreSelectButtonPopover",
    render: (h) => h("div", "Mocked Popover"),
}));

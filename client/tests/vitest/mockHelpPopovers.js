import { vi } from "vitest";
import { h } from "vue";

// bootstrap vue will try to match targets to actual HTML elements in DOM but there
// may be no DOM for vitest tests, just stub out an alternative minimal implementation.
vi.mock("@/components/Help/HelpPopover.vue", () => ({
    default: {
        name: "HelpPopover",
        render: () => h("div", "Mocked Popover"),
    },
}));

vi.mock("@/components/ObjectStore/ObjectStoreSelectButtonPopover.vue", () => ({
    default: {
        name: "ObjectStoreSelectButtonPopover",
        render: () => h("div", "Mocked Popover"),
    },
}));

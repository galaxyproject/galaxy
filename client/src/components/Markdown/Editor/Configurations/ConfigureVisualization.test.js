import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ConfigureVisualization from "./ConfigureVisualization.vue";

const localVue = getLocalVue();

const flushPromises = () => new Promise((resolve) => setTimeout(resolve));
const WARNING_HEADER = "This visualization configuration may have issues";

const fetchPlugin = vi.fn();
vi.mock("@/api/plugins", () => ({
    fetchPlugin: (...args) => fetchPlugin(...args),
}));

// settings is a closed object with one string field; the top level is open.
const SCHEMA = {
    type: "object",
    additionalProperties: true,
    properties: {
        settings: {
            anyOf: [
                {
                    type: "object",
                    additionalProperties: false,
                    properties: { locus: { anyOf: [{ type: "string" }, { type: "null" }], default: null } },
                },
                { type: "null" },
            ],
            default: null,
        },
        tracks: { type: "array", items: { type: "object", additionalProperties: true }, default: [] },
    },
};

function mountWith(content) {
    return mount(ConfigureVisualization, {
        localVue,
        pinia: createTestingPinia({ createSpy: vi.fn }),
        propsData: { content },
    });
}

describe("ConfigureVisualization.vue", () => {
    beforeEach(() => {
        fetchPlugin.mockReset();
        fetchPlugin.mockResolvedValue({ parameters_schema: SCHEMA });
    });

    it("shows no warning for a valid config", async () => {
        const wrapper = mountWith(JSON.stringify({ visualization_name: "demo", settings: { locus: "chr1" } }));
        await flushPromises();
        expect(fetchPlugin).toHaveBeenCalledWith("demo");
        expect(wrapper.text()).not.toContain(WARNING_HEADER);
    });

    it("warns about an unknown settings key without blocking", async () => {
        const wrapper = mountWith(JSON.stringify({ visualization_name: "demo", settings: { bogus: 1 } }));
        await flushPromises();
        expect(wrapper.text()).toContain(WARNING_HEADER);
        expect(wrapper.text()).toContain('unexpected property "bogus"');
    });

    it("does not fetch a schema when no visualization is named", async () => {
        const wrapper = mountWith(JSON.stringify({ settings: { locus: "chr1" } }));
        await flushPromises();
        expect(fetchPlugin).not.toHaveBeenCalled();
        expect(wrapper.text()).not.toContain(WARNING_HEADER);
    });

    it("stays quiet when the schema cannot be fetched", async () => {
        fetchPlugin.mockRejectedValue(new Error("no plugin"));
        const wrapper = mountWith(JSON.stringify({ visualization_name: "demo", settings: { bogus: 1 } }));
        await flushPromises();
        expect(wrapper.text()).not.toContain(WARNING_HEADER);
    });
});

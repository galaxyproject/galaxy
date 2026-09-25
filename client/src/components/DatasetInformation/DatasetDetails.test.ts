import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { sanitizeHtml } from "@/directives/sanitizeHtml";

import DatasetDetails from "./DatasetDetails.vue";

const PEEK = "<table><tr><td>col1</td></tr></table>";

vi.mock("@/api/datasets", async (importOriginal) => ({
    ...(await importOriginal<object>()),
    fetchDatasetDetails: vi.fn(async () => ({ id: "abc", creating_job: "job1", peek: PEEK })),
}));

vi.mock("@/composables/config", () => ({
    useConfig: () => ({ config: {}, isConfigLoaded: true }),
}));

const { server, http } = useServerMock();

describe("DatasetDetails", () => {
    it("renders the dataset peek through v-sanitize-html", async () => {
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) => response(200).json({ id: "job1", state: "ok" } as never)),
        );
        vi.mocked(sanitizeHtml).mockImplementation((html) => `<span class="sanitized">${html}</span>`);
        const wrapper = shallowMount(DatasetDetails as object, {
            localVue: getLocalVue(),
            pinia: createTestingPinia({ createSpy: vi.fn }),
            propsData: { datasetId: "abc" },
        });
        await flushPromises();

        expect(sanitizeHtml).toHaveBeenCalledWith(PEEK, "default");
        expect(wrapper.find(".dataset-peek .sanitized td").text()).toBe("col1");
    });
});

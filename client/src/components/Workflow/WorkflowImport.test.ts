import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import WorkflowImport from "./WorkflowImport.vue";
import TrsImport from "@/components/Workflow/Import/TrsImport.vue";

const mockRoute = vi.hoisted(() => ({ path: "/workflows/trs_import", query: {} as Record<string, string> }));
const mockPush = vi.hoisted(() => vi.fn());
const mockImportTrsToolFromUrl = vi.hoisted(() => vi.fn());

vi.mock("vue-router/composables", () => ({
    useRoute: () => mockRoute,
    useRouter: () => ({ push: mockPush }),
}));

vi.mock("@/components/Workflow/services", () => ({
    Services: class {
        getTrsServers() {
            return Promise.resolve([]);
        }
        importTrsToolFromUrl(url: string) {
            return mockImportTrsToolFromUrl(url);
        }
    },
}));

async function mountWithQuery(query: Record<string, string>) {
    mockRoute.query = query;
    const wrapper = mount(WorkflowImport as object, {
        localVue: getLocalVue(),
        pinia: createTestingPinia({ createSpy: vi.fn }),
    });
    await flushPromises();
    return wrapper;
}

const TRS_URL = "https://training.galaxyproject.org/training-material/api/ga4gh/trs/v2/tools/t-x/versions/wf";

describe("WorkflowImport", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("passes trs_version from GTN/Dockstore launch links on as the version to import", async () => {
        const wrapper = await mountWithQuery({
            trs_server: "dockstore.org",
            trs_id: "#workflow/github.com/org/repo/main",
            trs_version: "v0.1.3",
            run_form: "true",
        });
        const trsImport = wrapper.findComponent(TrsImport);
        expect(trsImport.exists()).toBe(true);
        expect(trsImport.props("queryTrsVersionId")).toBe("v0.1.3");
        expect(trsImport.props("isRun")).toBe(true);
    });

    it("still accepts trs_version_id", async () => {
        const wrapper = await mountWithQuery({ trs_id: "#workflow/x", trs_version_id: "main" });
        expect(wrapper.findComponent(TrsImport).props("queryTrsVersionId")).toBe("main");
    });

    it("imports trs_url launch links and opens the run form", async () => {
        mockImportTrsToolFromUrl.mockResolvedValue({ id: "imported-workflow" });
        await mountWithQuery({ trs_url: TRS_URL, run_form: "true" });
        expect(mockImportTrsToolFromUrl).toHaveBeenCalledTimes(1);
        expect(mockImportTrsToolFromUrl).toHaveBeenCalledWith(TRS_URL);
        expect(mockPush).toHaveBeenCalledWith({ path: "/workflows/run", query: { id: "imported-workflow" } });
    });
});

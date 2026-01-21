import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { waitOnJob } from "@/components/JobStates/wait";

import ToLink from "./ToLink.vue";

const localVue = getLocalVue();
const { server, http } = useServerMock();

const TEST_HISTORY_ID = "hist1235";
const TEST_EXPORTS_URL = `/api/histories/${TEST_HISTORY_ID}/exports`;
const TEST_JOB_ID = "test1234job";

vi.mock("@/components/JobStates/wait", () => ({
    waitOnJob: vi.fn(),
}));

describe("ToLink.vue", () => {
    let wrapper;

    async function mountWithInitialExports(exports) {
        server.use(
            http.untyped.get(TEST_EXPORTS_URL, () => {
                return HttpResponse.json(exports);
            }),
        );
        wrapper = shallowMount(ToLink, {
            propsData: {
                historyId: TEST_HISTORY_ID,
            },
            localVue,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find("loadingspan-stub").exists()).toBeTruthy();
        await flushPromises();
    }

    beforeEach(async () => {
        // Reset before each test
    });

    it("should display a link if no exports ever generated", async () => {
        await mountWithInitialExports([]);
        expect(wrapper.find(".export-link")).toBeTruthy();
        expect(wrapper.find("loadingspan-stub").exists()).toBeFalsy(); // loading span gone
    });

    it("should start polling if latest export is preparing", async () => {
        let then = null;
        vi.mocked(waitOnJob).mockReturnValue(
            new Promise((then_) => {
                then = then_;
            }),
        );
        await mountWithInitialExports([
            {
                preparing: true,
                job_id: TEST_JOB_ID,
            },
        ]);
        expect(then).toBeTruthy();
        expect(wrapper.vm.waitingOnJob).toBeTruthy();
        expect(wrapper.find("loadingspan-stub").exists()).toBeTruthy();
    });
});

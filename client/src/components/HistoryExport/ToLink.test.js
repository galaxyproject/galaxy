import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import ToLink from "./ToLink.vue";
import flushPromises from "flush-promises";
import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import { waitOnJob } from "components/JobStates/wait";

const localVue = getLocalVue();
const TEST_HISTORY_ID = "hist1235";
const TEST_EXPORTS_URL = `/api/histories/${TEST_HISTORY_ID}/exports`;
const TEST_JOB_ID = "test1234job";

jest.mock("components/JobStates/wait");

describe("ToLink.vue", () => {
    let axiosMock;
    let wrapper;

    async function mountWithInitialExports(exports) {
        axiosMock.onGet(TEST_EXPORTS_URL).reply(200, exports);
        wrapper = shallowMount(ToLink, {
            propsData: {
                historyId: TEST_HISTORY_ID,
            },
            localVue,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find("loading-span-stub").exists()).toBeTruthy();
        await flushPromises();
    }

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
    });

    it("should display a link if no exports ever generated", async () => {
        await mountWithInitialExports([]);
        expect(wrapper.find(".export-link")).toBeTruthy();
        expect(wrapper.find("loading-span-stub").exists()).toBeFalsy(); // loading span gone
    });

    it("should start polling if latest export is preparing", async () => {
        let then = null;
        waitOnJob.mockReturnValue(
            new Promise((then_) => {
                then = then_;
            })
        );
        await mountWithInitialExports([
            {
                preparing: true,
                job_id: TEST_JOB_ID,
            },
        ]);
        expect(then).toBeTruthy();
        expect(wrapper.vm.waitingOnJob).toBeTruthy();
        expect(wrapper.find("loading-span-stub").exists()).toBeTruthy();
    });

    afterEach(() => {
        axiosMock.restore();
    });
});

import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { mockFetcher } from "@/api/schema/__mocks__";
import { useUserStore } from "@/stores/userStore";

import QuotaMeter from "./QuotaMeter.vue";

jest.mock("@/api/schema");

const localVue = getLocalVue();

async function createQuotaMeterWrapper(config: any, userData: any) {
    mockFetcher.path("/api/configuration").method("get").mock({ data: config });
    const pinia = createTestingPinia();
    const userStore = useUserStore();
    userStore.currentUser = { ...userStore.currentUser, ...userData };

    const wrapper = mount(QuotaMeter, {
        localVue,
        pinia,
    });
    await flushPromises();
    return wrapper;
}

describe("QuotaMeter.vue", () => {
    it("shows a percentage usage", async () => {
        const user = {
            total_disk_usage: 5120,
            quota_percent: 50,
        };

        const config = { enable_quotas: true };
        const wrapper = await createQuotaMeterWrapper(config, user);

        expect(wrapper.find(".quota-progress > span").text()).toBe("Using 50%");
    });

    it("changes appearance depending on usage", async () => {
        const config = { enable_quotas: true };

        {
            const user = { quota_percent: 30 };
            const wrapper = await createQuotaMeterWrapper(config, user);

            expect(wrapper.find(".quota-progress .progress-bar").classes()).toContain("bg-success");
        }

        {
            const user = { quota_percent: 80 };
            const wrapper = await createQuotaMeterWrapper(config, user);

            expect(wrapper.find(".quota-progress .progress-bar").classes()).toContain("bg-warning");
        }

        {
            const user = { quota_percent: 95 };
            const wrapper = await createQuotaMeterWrapper(config, user);

            expect(wrapper.find(".quota-progress .progress-bar").classes()).toContain("bg-danger");
        }
    });

    it("prompts user to log in", async () => {
        const config = { enable_quotas: true };
        const wrapper = await createQuotaMeterWrapper(config, {});

        expect(wrapper.find(".quota-meter > a").attributes("title")).toContain("Log in");
    });

    it("shows total usage in title", async () => {
        const user = { total_disk_usage: 9216 };
        const config = { enable_quotas: true };
        const wrapper = await createQuotaMeterWrapper(config, user);

        expect(wrapper.find(".quota-progress").attributes("title")).toContain("9 KB");
    });

    it("shows total usage when there is no quota", async () => {
        {
            const user = { total_disk_usage: 7168 };
            const config = { enable_quotas: false };
            const wrapper = await createQuotaMeterWrapper(config, user);

            expect(wrapper.find(".quota-text > a").text()).toBe("Using 7 KB");
            expect(wrapper.find(".quota-text > a").attributes("title")).not.toContain("7 KB");
        }

        {
            const user = {
                total_disk_usage: 21504,
                quota: "unlimited",
            };

            const config = { enable_quotas: true };
            const wrapper = await createQuotaMeterWrapper(config, user);

            expect(wrapper.find(".quota-text > a").text()).toBe("Using 21 KB");
            expect(wrapper.find(".quota-text > a").attributes("title")).not.toContain("21 KB");
        }
    });
});

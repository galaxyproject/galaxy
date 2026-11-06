import { getFakeQuotaUsageData, getFakeStorage } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { toQuotaUsage } from "@/components/User/DiskUsage/Quota/model/QuotaUsage";

import FilterMenuDropdown from "./FilterMenuDropdown.vue";
import GDropdownItem from "@/components/BaseComponents/GDropdownItem.vue";

const localVue = getLocalVue();
const { server, http } = useServerMock();

const SCRATCH_USAGE = getFakeQuotaUsageData("scratch", 1);

async function mountQuotaSourceFilter(filters = {}) {
    server.use(
        http.get("/api/users/{user_id}/usage", ({ response }) =>
            response(200).json([getFakeQuotaUsageData(null, 1), SCRATCH_USAGE]),
        ),
        http.get("/api/object_stores", ({ response }) =>
            response(200).json([getFakeStorage("scratch", "Scratch Storage", { source: "scratch" })]),
        ),
    );
    const pinia = createPinia();
    setActivePinia(pinia);
    const wrapper = mount(FilterMenuDropdown as object, {
        props: {
            type: "QuotaSource",
            name: "quota_source",
            identifier: "test",
            filter: { placeholder: "storage source" },
            filters,
        },
        global: withPlugins(localVue, pinia),
    });
    await flushPromises();
    return wrapper;
}

describe("FilterMenuDropdown with quota sources", () => {
    it("names the options after the storages using each source", async () => {
        const wrapper = await mountQuotaSourceFilter();

        const options = wrapper.findAllComponents(GDropdownItem).map((item) => item.text());
        expect(options).toEqual(["(any)", "Default storage", "Scratch Storage"]);
    });

    it("names the selected source in the toggle", async () => {
        const wrapper = await mountQuotaSourceFilter({ quota_source: toQuotaUsage(SCRATCH_USAGE) });

        expect(wrapper.find("button").text()).toBe("Scratch Storage");
    });
});

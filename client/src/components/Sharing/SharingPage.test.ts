import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import axios from "axios";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { expect, it, vi } from "vitest";
import { ref } from "vue";
import type { RouteLocationNormalized } from "vue-router";

import { getRouter } from "@/entry/analysis/router";

import SharingPage from "./SharingPage.vue";

vi.mock("axios");
vi.mock("@/app", () => ({ getGalaxyInstance: () => ({ user: { get: () => "user" }, config: {} }) }));
vi.mock("@/composables/config", () => ({
    useConfig: () => ({ config: ref({}), isConfigLoaded: ref(true) }),
}));

it("shares notebooks through the pages API", async () => {
    const route = getRouter({ config: {}, user: {} }).resolve("/pages/sharing?id=a1") as RouteLocationNormalized;
    const props = (route.matched.at(-1)!.props.default as (r: RouteLocationNormalized) => object)(route);
    vi.mocked(axios.get).mockResolvedValue({
        data: { id: "a1", importable: true, published: true, users_shared_with: [] },
    });
    const localVue = getLocalVue(true);
    const wrapper = mount(SharingPage as object, {
        props,
        global: { ...localVue, plugins: [...(localVue.plugins ?? []), createPinia()] },
    });
    await flushPromises();
    expect(axios.get).toHaveBeenCalledWith("/api/pages/a1/sharing");
    expect(wrapper.find("a[href='/pages/list_published']").text()).toBe("Published Notebooks");
    await wrapper.find(".make-accessible input").setValue(false);
    expect(axios.put).toHaveBeenCalledWith("/api/pages/a1/disable_link_access", expect.anything());
});

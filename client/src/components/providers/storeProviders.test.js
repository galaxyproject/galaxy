import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import { DatatypesProvider } from "./storeProviders";

const localVue = getLocalVue();
const { server, http } = useServerMock();

describe("DatatypesProvider", () => {
    let wrapper;
    let datatypesRequests;

    beforeEach(() => {
        setActivePinia(createPinia());
        datatypesRequests = 0;
        // The provider logs the failure; keep test output quiet.
        vi.spyOn(console, "log").mockImplementation(() => {});
    });

    afterEach(() => {
        wrapper?.destroy();
        vi.restoreAllMocks();
    });

    it("stops loading when fetching datatypes fails", async () => {
        server.use(
            http.get("/api/datatypes", ({ response }) => {
                datatypesRequests++;
                return response.untyped(HttpResponse.json({ err_msg: "unavailable", err_code: 0 }, { status: 500 }));
            }),
        );
        wrapper = mount(DatatypesProvider, {
            localVue,
            propsData: { id: "datatypes" },
            scopedSlots: { default: '<span class="state">{{ props.loading }}</span>' },
        });
        await flushPromises();
        expect(datatypesRequests).toBe(1);
        expect(wrapper.find(".state").text()).toBe("false");
    });
});

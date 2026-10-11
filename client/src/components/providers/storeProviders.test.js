import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

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
    });

    afterEach(() => {
        wrapper?.destroy();
    });

    function mountProvider() {
        return mount(DatatypesProvider, {
            localVue,
            propsData: { id: "datatypes" },
            scopedSlots: {
                default:
                    '<div><span class="state">{{ props.loading }}</span><span class="error">{{ props.error }}</span></div>',
            },
        });
    }

    it("stops loading and exposes the error when fetching datatypes fails", async () => {
        server.use(
            http.get("/api/datatypes", ({ response }) => {
                datatypesRequests++;
                return response.untyped(HttpResponse.json({ err_msg: "unavailable", err_code: 0 }, { status: 500 }));
            }),
        );
        wrapper = mountProvider();
        await flushPromises();
        expect(datatypesRequests).toBe(1);
        expect(wrapper.find(".state").text()).toBe("false");
        expect(wrapper.find(".error").text()).toContain("unavailable");
    });

    it("exposes no error when fetching datatypes succeeds", async () => {
        server.use(
            http.get("/api/datatypes", ({ response }) => {
                datatypesRequests++;
                return response.untyped(HttpResponse.json([]));
            }),
        );
        wrapper = mountProvider();
        await flushPromises();
        expect(wrapper.find(".state").text()).toBe("false");
        expect(wrapper.find(".error").text()).toBe("");
    });
});

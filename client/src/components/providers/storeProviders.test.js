import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, disposePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, onTestFinished } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import { DatatypesProvider } from "./storeProviders";

const localVue = getLocalVue();
const { server, http } = useServerMock();

describe("DatatypesProvider", () => {
    let pinia;
    let datatypesRequests;

    beforeEach(() => {
        const ownedPinia = createPinia();
        pinia = ownedPinia;
        onTestFinished(() => disposePinia(ownedPinia));
        datatypesRequests = 0;
    });

    enableAutoUnmount(afterEach);

    function mountProvider() {
        return mount(DatatypesProvider, {
            global: withPlugins(localVue, pinia),
            props: { id: "datatypes" },
            slots: {
                default: `<template #default="props">
                    <div><span class="state">{{ props.loading }}</span><span class="error">{{ props.error }}</span></div>
                </template>`,
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
        const wrapper = mountProvider();
        await flushPromises();
        expect(datatypesRequests).toBe(1);
        expect(wrapper.get(".state").text()).toBe("false");
        expect(wrapper.get(".error").text()).toContain("unavailable");
    });

    it("exposes no error when fetching datatypes succeeds", async () => {
        server.use(
            http.get("/api/datatypes", ({ response }) => {
                datatypesRequests++;
                return response.untyped(HttpResponse.json([]));
            }),
        );
        const wrapper = mountProvider();
        await flushPromises();
        expect(wrapper.get(".state").text()).toBe("false");
        expect(wrapper.get(".error").text()).toBe("");
    });
});

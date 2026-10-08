import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import type Vue from "vue";
import { defineComponent, h } from "vue";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import HelpText from "./HelpText.vue";

const { server, http } = useServerMock();

const ROWS = 25;
const STATES = ["scheduled", "ready", "failed", "cancelled", "new"];

// Grid rows render one HelpText per invocation state, and each HelpText mounts its HelpTerm eagerly.
function mountHelpTexts(uris: string[]) {
    const Rows = defineComponent({
        render: () =>
            h(
                "div",
                uris.map((uri) => h(HelpText, { props: { uri, text: uri.split(".").pop() } })),
            ),
    });
    return mount(Rows as object, { localVue: getLocalVue(), pinia: createPinia(), attachTo: document.body });
}

describe("HelpText", () => {
    let datatypesRequests: number;
    let wrapper: Wrapper<Vue> | undefined;

    beforeEach(() => {
        datatypesRequests = 0;
        server.use(
            http.get("/api/datatypes", ({ response }) => {
                datatypesRequests++;
                return response.untyped(HttpResponse.json([]));
            }),
        );
    });

    afterEach(() => {
        wrapper?.destroy();
        wrapper = undefined;
    });

    it("renders invocation state help for many rows without requesting datatypes", async () => {
        const uris = Array.from({ length: ROWS }, (_, i) => `galaxy.invocations.states.${STATES[i % STATES.length]}`);
        wrapper = mountHelpTexts(uris);
        await flushPromises();
        expect(wrapper.findAll(".help-text")).toHaveLength(ROWS);
        expect(wrapper.text()).not.toContain("Loading Galaxy help terms");
        expect(wrapper.text()).toContain("has had all of its jobs scheduled");
        expect(datatypesRequests).toBe(0);
    });
});

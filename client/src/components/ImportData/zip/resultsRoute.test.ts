import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { defineComponent, h } from "vue";
import { createMemoryHistory, createRouter, RouterView } from "vue-router";

import { zipImportResultsLocation, zipImportResultsProps } from "./resultsRoute";

const Results = defineComponent({
    props: { workflowFileCount: Number, regularFileCount: Number },
    render() {
        return h("div");
    },
});

describe("zip import results route", () => {
    it("carries the counts from the wizard through to the results page", async () => {
        // Same path and props as the route in entry/analysis/router.js, which declares no params.
        const router = createRouter({
            history: createMemoryHistory(),
            routes: [
                { path: "/", component: Results },
                {
                    path: "/import/zip/results",
                    name: "ZipImportResults",
                    component: Results,
                    props: zipImportResultsProps,
                },
            ],
        });
        const wrapper = mount(RouterView, { global: { plugins: [router] } });

        await router.push(zipImportResultsLocation({ workflowFileCount: 2, regularFileCount: 3 }));

        const results = wrapper.findComponent(Results);
        expect(results.props("workflowFileCount")).toBe(2);
        expect(results.props("regularFileCount")).toBe(3);
    });
});

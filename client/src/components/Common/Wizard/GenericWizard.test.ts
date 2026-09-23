import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { defineComponent, h } from "vue";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import { useWizard } from "./useWizard";

import GenericWizard from "./GenericWizard.vue";

const Host = defineComponent({
    props: { description: { type: String, required: true } },
    setup(props) {
        const wizard = useWizard({
            only: { label: "Only step", instructions: "Do it", isValid: () => true, isSkippable: () => false },
        });
        return () => h(GenericWizard, { props: { use: wizard, description: props.description } });
    },
});

describe("GenericWizard", () => {
    it("renders the description markdown through v-sanitize-html with the links profile", () => {
        vi.mocked(sanitizeHtml).mockClear();
        mount(Host as object, {
            localVue: getLocalVue(),
            propsData: { description: "Pick **one** of the [options](https://example.org)" },
        });

        const call = vi.mocked(sanitizeHtml).mock.calls.find(([html]) => html?.includes("example.org"));
        expect(call?.[1]).toBe("links");
        expect(call?.[0]).toContain("<strong>one</strong>");
        expect(call?.[0]).toContain('target="_blank"');
    });
});

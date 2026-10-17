import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ObjectStoreRestrictionSpan from "./ObjectStoreRestrictionSpan.vue";

describe("ObjectStoreRestrictionSpan", () => {
    it.each([
        { isPrivate: true, text: "private", explanation: "restricted to a single user" },
        { isPrivate: false, text: "sharable", explanation: "allows standard Galaxy sharing features" },
    ])(
        "labels storage as $text and explains it on hover when isPrivate is $isPrivate",
        ({ isPrivate, text, explanation }) => {
            const wrapper = shallowMount(ObjectStoreRestrictionSpan, {
                props: { isPrivate },
                global: getLocalVue(),
            });

            const span = wrapper.get(".stored-how");
            expect(span.text()).toBe(text);
            expect(span.attributes("title")).toContain(explanation);
        },
    );
});

import { enableAutoUnmount, shallowMount } from "@vue/test-utils"
import { afterEach, describe, expect, it } from "vitest"

import JsonDiffViewer from "./JsonDiffViewer.vue"

enableAutoUnmount(afterEach)

describe("JsonDiffViewer", () => {
    it("renders the diff container", () => {
        const wrapper = shallowMount(JsonDiffViewer, {
            props: { before: { key: "value1" }, after: { key: "value2" } },
        })

        expect(wrapper.find(".json-diff-viewer").exists()).toBe(true)
    })

    const unchangedObject = { key: "value", nested: { a: 1 } }

    it.each([
        { name: "identical nested objects", before: unchangedObject, after: unchangedObject },
        { name: "empty objects", before: {}, after: {} },
    ])("shows no changes for $name", ({ before, after }) => {
        const wrapper = shallowMount(JsonDiffViewer, { props: { before, after } })

        expect(wrapper.get(".json-diff-viewer").text()).toBe("No changes detected")
    })

    it.each([
        {
            name: "a changed string",
            before: { name: "old" },
            after: { name: "new" },
            expectedText: ["old", "new"],
        },
        {
            name: "an added property",
            before: { existing: "value" },
            after: { existing: "value", added: "new value" },
            expectedText: ["added", "new value"],
        },
        {
            name: "a removed property",
            before: { existing: "value", removed: "old value" },
            after: { existing: "value" },
            expectedText: ["removed", "old value"],
        },
        {
            name: "a nested change",
            before: { nested: { value: "old" } },
            after: { nested: { value: "new" } },
            expectedText: ["nested", "value", "old", "new"],
        },
        {
            name: "an appended array item",
            before: { items: ["a", "b"] },
            after: { items: ["a", "b", "c"] },
            expectedText: ['"c"'],
        },
        {
            name: "a null value replaced by a string",
            before: { value: null },
            after: { value: "something" },
            expectedText: ["null", "something"],
        },
        {
            name: "a changed boolean",
            before: { flag: true },
            after: { flag: false },
            expectedText: ["flag", "true", "false"],
        },
        {
            name: "a changed number",
            before: { count: 1 },
            after: { count: 2 },
            expectedText: ["1", "2"],
        },
        {
            name: "a deeply nested change",
            before: { a: { b: { c: { d: "old" } } } },
            after: { a: { b: { c: { d: "new" } } } },
            expectedText: ["old", "new"],
        },
        {
            name: "a changed version in an array matched by ID",
            before: { tools: [{ id: "tool1", version: "1.0" }] },
            after: { tools: [{ id: "tool1", version: "2.0" }] },
            expectedText: ["version", "1.0", "2.0"],
        },
    ])("shows $name", ({ before, after, expectedText }) => {
        const wrapper = shallowMount(JsonDiffViewer, { props: { before, after } })
        const renderedDiff = wrapper.get(".json-diff-viewer").text()

        for (const text of expectedText) {
            expect(renderedDiff).toContain(text)
        }
    })
})

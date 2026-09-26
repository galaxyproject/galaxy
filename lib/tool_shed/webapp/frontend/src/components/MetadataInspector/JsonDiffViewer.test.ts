import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount } from "@vue/test-utils"
import JsonDiffViewer from "./JsonDiffViewer.vue"

describe("JsonDiffViewer", () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    describe("rendering", () => {
        it("renders diff container", () => {
            const wrapper = mount(JsonDiffViewer, {
                props: {
                    before: { key: "value1" },
                    after: { key: "value2" },
                },
            })

            expect(wrapper.find(".json-diff-viewer").exists()).toBe(true)
        })

        it("shows 'No changes detected' when objects are identical", () => {
            const data = { key: "value", nested: { a: 1 } }

            const wrapper = mount(JsonDiffViewer, {
                props: {
                    before: data,
                    after: data,
                },
            })

            expect(wrapper.text()).toContain("No changes detected")
        })

        it("detects and shows simple value changes", () => {
            const wrapper = mount(JsonDiffViewer, {
                props: {
                    before: { name: "old" },
                    after: { name: "new" },
                },
            })

            const html = wrapper.html()
            // jsondiffpatch adds CSS classes for modifications
            expect(html).toContain("old")
            expect(html).toContain("new")
        })
    })

    describe("diff detection", () => {
        it("detects added properties", () => {
            const wrapper = mount(JsonDiffViewer, {
                props: {
                    before: { existing: "value" },
                    after: { existing: "value", added: "new value" },
                },
            })

            expect(wrapper.html()).toContain("added")
        })

        it("detects removed properties", () => {
            const wrapper = mount(JsonDiffViewer, {
                props: {
                    before: { existing: "value", removed: "old value" },
                    after: { existing: "value" },
                },
            })

            expect(wrapper.html()).toContain("removed")
        })

        it("detects nested changes", () => {
            const wrapper = mount(JsonDiffViewer, {
                props: {
                    before: { nested: { value: "old" } },
                    after: { nested: { value: "new" } },
                },
            })

            const html = wrapper.html()
            expect(html).toContain("nested")
            expect(html).toContain("value")
        })

        it("detects array changes", () => {
            const wrapper = mount(JsonDiffViewer, {
                props: {
                    before: { items: ["a", "b"] },
                    after: { items: ["a", "b", "c"] },
                },
            })

            expect(wrapper.html()).toContain("c")
        })
    })

    describe("edge cases", () => {
        it("handles empty objects", () => {
            const wrapper = mount(JsonDiffViewer, {
                props: {
                    before: {},
                    after: {},
                },
            })

            expect(wrapper.text()).toContain("No changes detected")
        })

        it("handles null values", () => {
            const wrapper = mount(JsonDiffViewer, {
                props: {
                    before: { value: null },
                    after: { value: "something" },
                },
            })

            expect(wrapper.html()).toContain("something")
        })

        it("handles boolean changes", () => {
            const wrapper = mount(JsonDiffViewer, {
                props: {
                    before: { flag: true },
                    after: { flag: false },
                },
            })

            expect(wrapper.html()).toContain("flag")
        })

        it("handles numeric changes", () => {
            const wrapper = mount(JsonDiffViewer, {
                props: {
                    before: { count: 1 },
                    after: { count: 2 },
                },
            })

            expect(wrapper.html()).toContain("1")
            expect(wrapper.html()).toContain("2")
        })

        it("handles deeply nested objects", () => {
            const wrapper = mount(JsonDiffViewer, {
                props: {
                    before: { a: { b: { c: { d: "old" } } } },
                    after: { a: { b: { c: { d: "new" } } } },
                },
            })

            const html = wrapper.html()
            expect(html).toContain("old")
            expect(html).toContain("new")
        })

        it("handles arrays of objects with id-based matching", () => {
            const wrapper = mount(JsonDiffViewer, {
                props: {
                    before: {
                        tools: [{ id: "tool1", version: "1.0" }],
                    },
                    after: {
                        tools: [{ id: "tool1", version: "2.0" }],
                    },
                },
            })

            expect(wrapper.html()).toContain("version")
        })
    })
})

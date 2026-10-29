import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount } from "@vue/test-utils"
import MetadataJsonViewer from "./MetadataJsonViewer.vue"

// Mock vue-json-pretty to render JSON as text for assertions
vi.mock("vue-json-pretty", () => ({
    default: {
        name: "VueJsonPretty",
        props: ["data", "virtual", "showLength", "deep"],
        template: `
            <div class="vue-json-pretty">
                <pre>{{ JSON.stringify(data, null, 2) }}</pre>
            </div>
        `,
    },
}))

vi.mock("vue-json-pretty/lib/styles.css", () => ({}))

describe("MetadataJsonViewer", () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    describe("rendering", () => {
        it("renders JSON data", () => {
            const wrapper = mount(MetadataJsonViewer, {
                props: {
                    data: { name: "test", version: "1.0" },
                },
            })

            expect(wrapper.text()).toContain("test")
            expect(wrapper.text()).toContain("1.0")
        })

        it("renders nested objects", () => {
            const wrapper = mount(MetadataJsonViewer, {
                props: {
                    data: {
                        tool: {
                            id: "my_tool",
                            inputs: [{ name: "input1" }],
                        },
                    },
                },
            })

            expect(wrapper.text()).toContain("my_tool")
            expect(wrapper.text()).toContain("input1")
        })

        it("renders arrays", () => {
            const wrapper = mount(MetadataJsonViewer, {
                props: {
                    data: {
                        items: ["one", "two", "three"],
                    },
                },
            })

            expect(wrapper.text()).toContain("one")
            expect(wrapper.text()).toContain("two")
            expect(wrapper.text()).toContain("three")
        })

        it("renders the vue-json-pretty component", () => {
            const wrapper = mount(MetadataJsonViewer, {
                props: {
                    data: { key: "value" },
                },
            })

            expect(wrapper.find(".vue-json-pretty").exists()).toBe(true)
        })
    })

    describe("props", () => {
        it("accepts modelName prop", () => {
            const wrapper = mount(MetadataJsonViewer, {
                props: {
                    data: { tools: [] },
                    modelName: "RepositoryRevisionMetadata",
                },
            })

            expect(wrapper.find(".vue-json-pretty").exists()).toBe(true)
        })

        it("accepts deep prop for expansion depth", () => {
            const wrapper = mount(MetadataJsonViewer, {
                props: {
                    data: { nested: { data: "value" } },
                    deep: 5,
                },
            })

            expect(wrapper.find(".vue-json-pretty").exists()).toBe(true)
        })
    })

    describe("edge cases", () => {
        it("handles empty object", () => {
            const wrapper = mount(MetadataJsonViewer, {
                props: {
                    data: {},
                },
            })

            expect(wrapper.find(".vue-json-pretty").exists()).toBe(true)
        })

        it("handles null values in data", () => {
            const wrapper = mount(MetadataJsonViewer, {
                props: {
                    data: { value: null },
                },
            })

            expect(wrapper.text()).toContain("null")
        })

        it("handles boolean values", () => {
            const wrapper = mount(MetadataJsonViewer, {
                props: {
                    data: { enabled: true, disabled: false },
                },
            })

            expect(wrapper.text()).toContain("true")
            expect(wrapper.text()).toContain("false")
        })

        it("handles numeric values", () => {
            const wrapper = mount(MetadataJsonViewer, {
                props: {
                    data: { count: 42, price: 19.99 },
                },
            })

            expect(wrapper.text()).toContain("42")
            expect(wrapper.text()).toContain("19.99")
        })

        it("handles deeply nested data", () => {
            const wrapper = mount(MetadataJsonViewer, {
                props: {
                    data: {
                        level1: {
                            level2: {
                                level3: {
                                    level4: {
                                        value: "deep",
                                    },
                                },
                            },
                        },
                    },
                },
            })

            expect(wrapper.text()).toContain("deep")
        })

        it("handles large arrays", () => {
            const largeArray = Array.from({ length: 100 }, (_, i) => ({ id: i, name: `item${i}` }))

            const wrapper = mount(MetadataJsonViewer, {
                props: {
                    data: { items: largeArray },
                },
            })

            expect(wrapper.find(".vue-json-pretty").exists()).toBe(true)
            expect(wrapper.text()).toContain("item99")
        })
    })
})

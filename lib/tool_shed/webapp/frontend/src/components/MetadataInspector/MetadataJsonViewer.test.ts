import { mount, enableAutoUnmount } from "@vue/test-utils"
import { afterEach, describe, it, expect, vi } from "vitest"

import MetadataJsonViewer from "./MetadataJsonViewer.vue"

vi.mock("vue-json-pretty", async () => {
    const { defineComponent, h } = await import("vue")
    return {
        default: defineComponent({
            name: "VueJsonPretty",
            props: {
                data: { type: [Object, Array, String, Number, Boolean], required: true },
                virtual: { type: Boolean, default: undefined },
                showLength: { type: Boolean, default: undefined },
                deep: { type: Number, default: undefined },
            },
            setup(props) {
                return () => h("div", { class: "vue-json-pretty" }, [h("pre", JSON.stringify(props.data, null, 2))])
            },
        }),
    }
})

enableAutoUnmount(afterEach)

function mountViewer(props: InstanceType<typeof MetadataJsonViewer>["$props"]) {
    return mount(MetadataJsonViewer, { props })
}

describe("MetadataJsonViewer", () => {
    describe("rendering", () => {
        it("passes JSON data to the renderer", () => {
            const wrapper = mountViewer({ data: { name: "test", version: "1.0" } })

            expect(wrapper.text()).toContain("test")
            expect(wrapper.text()).toContain("1.0")
        })

        it("passes nested objects to the renderer", () => {
            const wrapper = mountViewer({
                data: {
                    tool: {
                        id: "my_tool",
                        inputs: [{ name: "input1" }],
                    },
                },
            })

            expect(wrapper.text()).toContain("my_tool")
            expect(wrapper.text()).toContain("input1")
        })

        it("passes array entries to the renderer", () => {
            const wrapper = mountViewer({ data: { items: ["one", "two", "three"] } })

            expect(wrapper.text()).toContain("one")
            expect(wrapper.text()).toContain("two")
            expect(wrapper.text()).toContain("three")
        })

        it("renders VueJsonPretty with nonvirtual output and array lengths", () => {
            const wrapper = mountViewer({ data: { key: "value" } })

            expect(wrapper.find(".vue-json-pretty").exists()).toBe(true)
            expect(wrapper.getComponent({ name: "VueJsonPretty" }).props()).toEqual({
                data: { key: "value" },
                virtual: false,
                showLength: true,
                deep: 2,
            })
        })
    })

    describe("props", () => {
        it("renders with a metadata model name", () => {
            const wrapper = mountViewer({
                data: { tools: [] },
                modelName: "RepositoryRevisionMetadata",
            })

            expect(wrapper.find(".vue-json-pretty").exists()).toBe(true)
        })

        it("passes a custom expansion depth to the renderer", () => {
            const wrapper = mountViewer({ data: { nested: { data: "value" } }, deep: 5 })

            expect(wrapper.find(".vue-json-pretty").exists()).toBe(true)
            expect(wrapper.getComponent({ name: "VueJsonPretty" }).props("deep")).toBe(5)
        })
    })

    describe("JSON values", () => {
        it("accepts an empty object", () => {
            const wrapper = mountViewer({ data: {} })

            expect(wrapper.find(".vue-json-pretty").exists()).toBe(true)
        })

        it("passes null values to the renderer", () => {
            const wrapper = mountViewer({ data: { value: null } })

            expect(wrapper.text()).toContain("null")
        })

        it("passes boolean values to the renderer", () => {
            const wrapper = mountViewer({ data: { enabled: true, disabled: false } })

            expect(wrapper.text()).toContain("true")
            expect(wrapper.text()).toContain("false")
        })

        it("passes numeric values to the renderer", () => {
            const wrapper = mountViewer({ data: { count: 42, price: 19.99 } })

            expect(wrapper.text()).toContain("42")
            expect(wrapper.text()).toContain("19.99")
        })

        it("passes deeply nested data to the renderer", () => {
            const wrapper = mountViewer({
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
            })

            expect(wrapper.text()).toContain("deep")
        })

        it("passes all 100 array entries to the renderer", () => {
            const items = Array.from({ length: 100 }, (_, i) => ({ id: i, name: `item${i}` }))
            const wrapper = mountViewer({ data: { items } })

            expect(wrapper.find(".vue-json-pretty").exists()).toBe(true)
            expect(wrapper.text()).toContain("item99")
        })
    })
})

import { GButton, GCollapse, GDropdownItem, GLink, GTab, GTabs } from "@galaxyproject/galaxy-ui"
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { afterEach, describe, expect, it, vi } from "vitest"
import { createMemoryRouter } from "@/test-utils"

enableAutoUnmount(afterEach)

/**
 * The galaxy-ui package ships raw source. The Galaxy client compiles it under
 * @vue/compat, which still emulates Vue 2 behaviour such as `.native` listeners;
 * this app compiles it on plain Vue 3. Anything compat smooths over -- listener
 * fallthrough, attribute merging -- only shows up here.
 *
 * These cover the plain Vue 3 side, kept next to the first external consumer
 * that depends on it.
 */
describe("galaxy-ui under Vue 3", () => {
    it("emits one click per click", async () => {
        // Vue 3 merges listeners into $attrs, so a component that both spreads
        // $attrs onto its root and emits its own click hands the caller two
        // calls for one press.
        const onClick = vi.fn()
        const wrapper = mount(GButton, {
            props: { color: "blue" },
            attrs: { onClick },
            slots: { default: "Press" },
        })

        await wrapper.find("button").trigger("click")

        expect(onClick).toHaveBeenCalledTimes(1)
    })

    it("emits one click per click from GLink", async () => {
        const onClick = vi.fn()
        const wrapper = mount(GLink, {
            attrs: { onClick },
            slots: { default: "Go" },
        })

        await wrapper.find("button").trigger("click")

        expect(onClick).toHaveBeenCalledTimes(1)
    })

    it.each([
        ["GButton", GButton, { color: "blue", to: "/target" }],
        ["GLink", GLink, { to: "/target" }],
        ["GDropdownItem", GDropdownItem, { to: "/target" }],
    ])("emits one click per click from a router-linked %s", async (_name, component, props) => {
        // A RouterLink root gets the click listener by fallthrough onto its <a>
        const onClick = vi.fn()
        const wrapper = mount(component, {
            props,
            attrs: { onClick },
            slots: { default: "Go" },
            global: { plugins: [createMemoryRouter()] },
        })

        await wrapper.find("a").trigger("click")

        expect(onClick).toHaveBeenCalledTimes(1)
    })

    it("does not click through when disabled", async () => {
        const onClick = vi.fn()
        const wrapper = mount(GButton, {
            props: { color: "blue", disabled: true },
            attrs: { onClick },
            slots: { default: "Press" },
        })

        await wrapper.find("button").trigger("click")

        expect(onClick).not.toHaveBeenCalled()
    })
})

// Vue 2's value/input v-model only works where @vue/compat maps it; here it silently does nothing.
// On plain Vue 3, v-model on a component compiles to the modelValue prop and update:modelValue listener.
describe("galaxy-ui v-model under Vue 3", () => {
    it("binds the active tab both ways on GTabs", async () => {
        const wrapper = mount(GTabs, {
            props: {
                modelValue: 1,
                "onUpdate:modelValue": (index: number) => wrapper.setProps({ modelValue: index }),
            },
            slots: { default: `<GTab title="One">one</GTab><GTab title="Two">two</GTab>` },
            global: { components: { GTab } },
        })
        await flushPromises()

        expect(wrapper.get(".nav-link.active").text()).toBe("Two")

        await wrapper.get(".nav-link").trigger("click")

        expect(wrapper.emitted("update:modelValue")).toEqual([[0]])
        expect(wrapper.get(".nav-link.active").text()).toBe("One")
    })

    it("opens GCollapse from its v-model", async () => {
        const wrapper = mount(GCollapse, {
            props: { modelValue: false },
            slots: { default: "details" },
        })
        await flushPromises()
        expect(wrapper.classes()).not.toContain("g-collapse-open")

        await wrapper.setProps({ modelValue: true })
        await flushPromises()

        expect(wrapper.classes()).toContain("g-collapse-open")
    })
})

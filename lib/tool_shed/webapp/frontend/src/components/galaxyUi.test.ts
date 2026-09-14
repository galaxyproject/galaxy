import { GButton, GDropdownItem, GLink } from "@galaxyproject/galaxy-ui"
import { mount } from "@vue/test-utils"
import { describe, expect, it, vi } from "vitest"
import { createMemoryHistory, createRouter } from "vue-router"

function makeRouter() {
    return createRouter({
        history: createMemoryHistory(),
        routes: [{ path: "/:any(.*)*", component: { template: "<div />" } }],
    })
}

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
        const router = makeRouter()
        const wrapper = mount(component, {
            props,
            attrs: { onClick },
            slots: { default: "Go" },
            global: { plugins: [router] },
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

import { afterEach, describe, it, expect } from "vitest"
import { enableAutoUnmount, mount, flushPromises, type VueWrapper } from "@vue/test-utils"
import ErrorBanner from "./ErrorBanner.vue"

const BANNER = '[role="alert"]'

enableAutoUnmount(afterEach)

function mountBanner(error: string) {
    return mount(ErrorBanner, { props: { error } })
}

async function clickDismiss(wrapper: VueWrapper) {
    await wrapper.find("button").trigger("click")
    await flushPromises()
}

describe("ErrorBanner", () => {
    describe("rendering", () => {
        it("displays the error message", () => {
            const wrapper = mountBanner("Something went wrong")

            expect(wrapper.text()).toContain("Something went wrong")
        })

        it("renders no banner for an empty error", () => {
            const wrapper = mountBanner("")

            expect(wrapper.find(BANNER).exists()).toBe(false)
        })

        it("announces the error assertively to assistive technology", () => {
            const wrapper = mountBanner("Test error")

            const banner = wrapper.find(BANNER)
            expect(banner.exists()).toBe(true)
            expect(banner.attributes("aria-live")).toBe("assertive")
        })

        it("displays a long error message in full", () => {
            const longError =
                "This is a very long error message that might wrap or cause layout issues in the UI, but should still be displayed correctly to the user."

            const wrapper = mountBanner(longError)

            expect(wrapper.text()).toContain(longError)
        })

        it("displays markup in the error message as escaped text", () => {
            const specialError = "Error: <script>alert('xss')</script> & 'quotes'"

            const wrapper = mountBanner(specialError)

            expect(wrapper.text()).toContain(specialError)
            expect(wrapper.find("script").exists()).toBe(false)
        })
    })

    describe("dismissing", () => {
        it("hides the banner when its Dismiss button is clicked", async () => {
            const wrapper = mountBanner("Test error message")
            expect(wrapper.find(BANNER).exists()).toBe(true)
            expect(wrapper.find("button").text()).toBe("Dismiss")

            await clickDismiss(wrapper)

            expect(wrapper.find(BANNER).exists()).toBe(false)
        })

        it("emits a single dismiss event when its Dismiss button is clicked", async () => {
            const wrapper = mountBanner("Test error")

            await clickDismiss(wrapper)

            expect(wrapper.emitted("dismiss")).toEqual([[]])
        })
    })

    describe("error prop changes", () => {
        it("shows the banner again with a new error after it was dismissed", async () => {
            const wrapper = mountBanner("First error")
            await clickDismiss(wrapper)
            expect(wrapper.find(BANNER).exists()).toBe(false)

            await wrapper.setProps({ error: "Second error" })

            expect(wrapper.find(BANNER).exists()).toBe(true)
            expect(wrapper.text()).toContain("Second error")
        })

        it("replaces the displayed message with the new error", async () => {
            const wrapper = mountBanner("Initial error")
            expect(wrapper.text()).toContain("Initial error")

            await wrapper.setProps({ error: "Updated error" })

            expect(wrapper.text()).toContain("Updated error")
            expect(wrapper.text()).not.toContain("Initial error")
        })
    })
})

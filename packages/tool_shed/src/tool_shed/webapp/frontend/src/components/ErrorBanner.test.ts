import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount, flushPromises } from "@vue/test-utils"
import { nextTick } from "vue"
import ErrorBanner from "./ErrorBanner.vue"

describe("ErrorBanner", () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    describe("rendering", () => {
        it("displays error message when error prop is provided", () => {
            const wrapper = mount(ErrorBanner, {
                props: {
                    error: "Something went wrong",
                },
            })

            expect(wrapper.text()).toContain("Something went wrong")
        })

        it("does not display banner when error prop is empty", () => {
            const wrapper = mount(ErrorBanner, {
                props: {
                    error: "",
                },
            })

            const banner = wrapper.find('[role="alert"]')
            expect(banner.exists()).toBe(false)
        })

        it("has correct ARIA attributes for accessibility", () => {
            const wrapper = mount(ErrorBanner, {
                props: {
                    error: "Test error",
                },
            })

            const banner = wrapper.find('[role="alert"]')
            expect(banner.exists()).toBe(true)
            expect(banner.attributes("aria-live")).toBe("assertive")
        })
    })

    describe("dismiss functionality", () => {
        it("hides banner when dismiss button is clicked", async () => {
            const wrapper = mount(ErrorBanner, {
                props: {
                    error: "Test error message",
                },
            })

            // Banner should be visible initially
            expect(wrapper.find('[role="alert"]').exists()).toBe(true)

            // Find and click dismiss button (button has label "Dismiss")
            const button = wrapper.find("button")
            expect(button.exists()).toBe(true)
            expect(button.text()).toBe("Dismiss")
            await button.trigger("click")

            await flushPromises()

            // Banner should be hidden after dismiss
            expect(wrapper.find('[role="alert"]').exists()).toBe(false)
        })

        it("emits dismiss event when dismiss button is clicked", async () => {
            const wrapper = mount(ErrorBanner, {
                props: {
                    error: "Test error",
                },
            })

            const button = wrapper.find("button")
            await button.trigger("click")
            await flushPromises()

            expect(wrapper.emitted("dismiss")).toBeTruthy()
            expect(wrapper.emitted("dismiss")).toHaveLength(1)
        })
    })

    describe("error prop changes", () => {
        it("shows banner again when error prop changes after dismiss", async () => {
            const wrapper = mount(ErrorBanner, {
                props: {
                    error: "First error",
                },
            })

            // Dismiss the banner
            const button = wrapper.find("button")
            await button.trigger("click")
            await flushPromises()

            expect(wrapper.find('[role="alert"]').exists()).toBe(false)

            // Change error prop
            await wrapper.setProps({ error: "Second error" })
            await nextTick()
            await flushPromises()

            // Banner should be visible again with new error
            expect(wrapper.find('[role="alert"]').exists()).toBe(true)
            expect(wrapper.text()).toContain("Second error")
        })

        it("displays new error message when error prop changes", async () => {
            const wrapper = mount(ErrorBanner, {
                props: {
                    error: "Initial error",
                },
            })

            expect(wrapper.text()).toContain("Initial error")

            await wrapper.setProps({ error: "Updated error" })
            await flushPromises()

            expect(wrapper.text()).toContain("Updated error")
            expect(wrapper.text()).not.toContain("Initial error")
        })
    })

    describe("edge cases", () => {
        it("handles long error messages", () => {
            const longError =
                "This is a very long error message that might wrap or cause layout issues in the UI, but should still be displayed correctly to the user."

            const wrapper = mount(ErrorBanner, {
                props: {
                    error: longError,
                },
            })

            expect(wrapper.text()).toContain(longError)
        })

        it("handles special characters in error message", () => {
            const specialError = "Error: <script>alert('xss')</script> & 'quotes'"

            const wrapper = mount(ErrorBanner, {
                props: {
                    error: specialError,
                },
            })

            // Should display the error text (Vue escapes HTML by default)
            expect(wrapper.text()).toContain("Error:")
            expect(wrapper.text()).toContain("quotes")
        })
    })
})

import { describe, it, expect, afterEach, beforeEach, vi } from "vitest"
import { enableAutoUnmount, mount } from "@vue/test-utils"
import LandingSearchBox from "./LandingSearchBox.vue"

const mockPush = vi.fn()
vi.mock("vue-router", () => ({
    useRouter: () => ({ push: mockPush }),
}))

enableAutoUnmount(afterEach)

describe("LandingSearchBox", () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    // Enter in the input submits the form natively, which also skips the Enter that confirms an IME composition
    it("navigates to the search results when the form is submitted", async () => {
        const wrapper = mount(LandingSearchBox)

        await wrapper.find("input").setValue("bowtie")
        await wrapper.find("form[role='search']").trigger("submit")

        expect(mockPush).toHaveBeenCalledWith({
            path: "/repositories_by_search",
            query: { q: "bowtie" },
        })
    })

    it("navigates to the search results when the search button is clicked", async () => {
        const wrapper = mount(LandingSearchBox, { attachTo: document.body })

        await wrapper.find("input").setValue("  samtools  ")
        await wrapper.find("button[type='submit']").trigger("click")

        expect(mockPush).toHaveBeenCalledWith({
            path: "/repositories_by_search",
            query: { q: "samtools" },
        })
    })

    it("does not navigate for a blank query", async () => {
        const wrapper = mount(LandingSearchBox)

        await wrapper.find("input").setValue("   ")
        await wrapper.find("button[type='submit']").trigger("click")

        expect(mockPush).not.toHaveBeenCalled()
    })
})

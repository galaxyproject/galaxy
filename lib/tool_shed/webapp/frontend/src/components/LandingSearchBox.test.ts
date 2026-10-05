import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount } from "@vue/test-utils"
import LandingSearchBox from "./LandingSearchBox.vue"

const mockPush = vi.fn()
vi.mock("vue-router", () => ({
    useRouter: () => ({ push: mockPush }),
}))

describe("LandingSearchBox", () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it("navigates to the search results on enter", async () => {
        const wrapper = mount(LandingSearchBox)

        const input = wrapper.find("input")
        await input.setValue("bowtie")
        await input.trigger("keydown", { key: "Enter" })

        expect(mockPush).toHaveBeenCalledWith({
            path: "/repositories_by_search",
            query: { q: "bowtie" },
        })
    })

    it("searches once for a held Enter and ignores the Enter that confirms an IME composition", async () => {
        const wrapper = mount(LandingSearchBox)

        const input = wrapper.find("input")
        await input.setValue("bowtie")
        await input.trigger("keydown", { key: "Enter" })
        await input.trigger("keydown", { key: "Enter", repeat: true })
        await input.trigger("keydown", { key: "Enter", isComposing: true })

        expect(mockPush).toHaveBeenCalledTimes(1)
    })

    it("navigates to the search results when the search button is clicked", async () => {
        const wrapper = mount(LandingSearchBox)

        await wrapper.find("input").setValue("  samtools  ")
        await wrapper.find("button[aria-label='Search']").trigger("click")

        expect(mockPush).toHaveBeenCalledWith({
            path: "/repositories_by_search",
            query: { q: "samtools" },
        })
    })

    it("does not navigate for a blank query", async () => {
        const wrapper = mount(LandingSearchBox)

        await wrapper.find("input").setValue("   ")
        await wrapper.find("button[aria-label='Search']").trigger("click")

        expect(mockPush).not.toHaveBeenCalled()
    })
})

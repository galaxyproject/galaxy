import { enableAutoUnmount, mount, flushPromises } from "@vue/test-utils"
import { createPinia, disposePinia, setActivePinia } from "pinia"
import { afterEach, describe, expect, it, onTestFinished, vi } from "vitest"
import { useCategoriesStore } from "@/stores"
import { createMemoryRouter } from "@/test-utils"
import RepositoriesByCategories from "./RepositoriesByCategories.vue"

describe("RepositoriesByCategories", () => {
    afterEach(() => {
        vi.restoreAllMocks()
    })
    enableAutoUnmount(afterEach)

    it("links each category and hides the dependency-packages category", async () => {
        const pinia = createPinia()
        onTestFinished(() => disposePinia(pinia))
        setActivePinia(pinia)
        const store = useCategoriesStore(pinia)
        vi.spyOn(store, "getAll").mockResolvedValue(undefined)
        store.$patch({
            loading: false,
            categories: [
                { id: "c1", name: "Assembly", description: "Assemblers", repositories: 3 },
                { id: "c2", name: "Tool Dependency Packages", description: "Packages", repositories: 9 },
            ],
        })

        const wrapper = mount(RepositoriesByCategories, {
            global: {
                plugins: [pinia, createMemoryRouter()],
                stubs: { PageContainer: { template: "<div><slot /></div>" } },
            },
        })
        await flushPromises()

        const rows = wrapper.findAll("tbody tr")
        expect(rows).toHaveLength(1)
        expect(wrapper.get("tbody tr a").attributes("href")).toBe("/repositories_by_category/c1")
        expect(wrapper.get("tbody tr").text()).toContain("Assemblers")
        expect(wrapper.get("caption").text()).toBe("Categories")
    })
})

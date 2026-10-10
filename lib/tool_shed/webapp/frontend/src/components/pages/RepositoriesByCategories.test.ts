import { mount, flushPromises } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { useCategoriesStore } from "@/stores"
import { createMemoryRouter } from "@/test-utils"
import RepositoriesByCategories from "./RepositoriesByCategories.vue"

describe("RepositoriesByCategories", () => {
    beforeEach(() => {
        setActivePinia(createPinia())
    })

    it("links each category and hides the dependency-packages category", async () => {
        const store = useCategoriesStore()
        vi.spyOn(store, "getAll").mockResolvedValue(undefined)
        store.$patch({
            loading: false,
            categories: [
                { id: "c1", name: "Assembly", description: "Assemblers", repositories: 3 },
                { id: "c2", name: "Tool Dependency Packages", description: "Packages", repositories: 9 },
            ],
        })

        const wrapper = mount(RepositoriesByCategories, {
            global: { plugins: [createMemoryRouter()], stubs: { PageContainer: { template: "<div><slot /></div>" } } },
        })
        await flushPromises()

        const rows = wrapper.findAll("tbody tr")
        expect(rows).toHaveLength(1)
        expect(rows[0].get("a").attributes("href")).toBe("/repositories_by_category/c1")
        expect(rows[0].text()).toContain("Assemblers")
        expect(wrapper.get("caption").text()).toBe("Categories")
    })
})

import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it } from "vitest"
import { createMemoryHistory, createRouter } from "vue-router"
import { useAuthStore } from "@/stores"
import RepositoryActions from "./RepositoryActions.vue"
import RepositoryExplore from "./RepositoryExplore.vue"
import RepositoryHealth from "./RepositoryHealth.vue"

const repository = { id: "abc", name: "bismark", owner: "devteam" }

function withRouter() {
    const router = createRouter({
        history: createMemoryHistory(),
        routes: [{ path: "/:any(.*)*", component: { template: "<div />" } }],
    })
    return { global: { plugins: [router] }, attachTo: document.body }
}

describe("RepositoryHealth", () => {
    it("lists downloadability, installs and last update as readable facts", () => {
        const wrapper = mount(RepositoryHealth, {
            props: { downloadable: true, installs: 12, lastUpdated: new Date().toISOString().replace("Z", "") },
        })
        const pills = wrapper.findAll(".health-pill").map((pill) => pill.text())

        expect(pills[0]).toBe("Downloadable")
        expect(pills[1]).toBe("12 installs")
        expect(pills[2]).toMatch(/^Updated .+ ago$/)
        expect(wrapper.get(".health-pill").classes()).toContain("health-ok")
    })

    it("flags a repository that cannot be downloaded and counts a single install", () => {
        const wrapper = mount(RepositoryHealth, {
            props: { downloadable: false, installs: 1, lastUpdated: "2024-01-01T00:00:00" },
        })
        const pills = wrapper.findAll(".health-pill")

        expect(pills[0].text()).toBe("Not downloadable")
        expect(pills[0].classes()).toContain("health-problem")
        expect(pills[1].text()).toBe("1 install")
    })
})

describe("RepositoryActions", () => {
    it("names its menu and offers to deprecate an active repository", async () => {
        const wrapper = mount(RepositoryActions, { props: { repositoryId: "abc", deprecated: false }, ...withRouter() })

        expect(wrapper.get(".action-menu-toggle").attributes("aria-label")).toBe("Repository settings")
        const deprecate = wrapper.findAll(".dropdown-item").find((item) => item.text() === "Mark as Deprecated")
        await deprecate?.trigger("click")

        expect(wrapper.emitted("deprecate")).toHaveLength(1)
    })

    it("offers to un-deprecate a deprecated repository", async () => {
        const wrapper = mount(RepositoryActions, { props: { repositoryId: "abc", deprecated: true }, ...withRouter() })

        const undeprecate = wrapper.findAll(".dropdown-item").find((item) => item.text() === "Un-mark as Deprecated")
        await undeprecate?.trigger("click")

        expect(wrapper.emitted("undeprecate")).toHaveLength(1)
        expect(wrapper.findAll(".dropdown-item").map((item) => item.text())).not.toContain("Mark as Deprecated")
    })
})

describe("RepositoryExplore", () => {
    beforeEach(() => {
        setActivePinia(createPinia())
    })

    function mountExplore(props: Record<string, unknown>, user: Record<string, unknown> | null = null) {
        useAuthStore().user = user
        return mount(RepositoryExplore, { props: { repository, ...props }, ...withRouter() })
    }

    function menuLinks(wrapper: ReturnType<typeof mountExplore>) {
        return wrapper.findAll("a.dropdown-item").map((link) => [link.text(), link.attributes("href")])
    }

    function denseButtons(wrapper: ReturnType<typeof mountExplore>) {
        return wrapper.findAll(".repository-explore-buttons .g-button").map((b) => b.attributes("aria-label"))
    }

    it("links the contents of the browsable revision from the explore menu", () => {
        const wrapper = mountExplore({ browsableRevision: "r1" })

        expect(menuLinks(wrapper)).toEqual([["Contents", "/repositories/abc/contents?revision=r1"]])
    })

    it("links the newest contents when there is no browsable revision", () => {
        const wrapper = mountExplore({})

        expect(menuLinks(wrapper)).toEqual([["Contents", "/repositories/abc/contents"]])
    })

    it("adds the hgweb changelog for logged in users", () => {
        const wrapper = mountExplore({ browsableRevision: "r1" }, { username: "bob" })

        expect(menuLinks(wrapper)).toEqual([
            ["Changelog", "/repos/devteam/bismark/shortlog"],
            ["Contents", "/repositories/abc/contents?revision=r1"],
        ])
    })

    it("shows labelled icon buttons in dense mode, including the optional external links", () => {
        const wrapper = mountExplore({
            repository: { ...repository, homepage_url: "https://example.org", remote_repository_url: null },
            dense: true,
        })

        expect(denseButtons(wrapper)).toEqual(["Details", "Metadata Inspector", "Contents", "Homepage"])
        expect(wrapper.get('[aria-label="Contents"]').attributes("href")).toBe("/repositories/abc/contents")
        expect(wrapper.get('[aria-label="Homepage"]').attributes("href")).toBe("https://example.org")
    })

    it.each(["deprecated", "deleted"])("leaves Contents out for a %s repository, whose files 404", (flag) => {
        const menu = mountExplore({ repository: { ...repository, [flag]: true } })
        const dense = mountExplore({ repository: { ...repository, [flag]: true }, dense: true })

        expect(menuLinks(menu)).toEqual([])
        expect(denseButtons(dense)).toEqual(["Details", "Metadata Inspector"])
    })

    it("adds the changelog button in dense mode for logged in users", () => {
        const wrapper = mountExplore({ dense: true }, { username: "bob" })

        expect(denseButtons(wrapper)).toEqual(["Details", "Metadata Inspector", "Changelog", "Contents"])
        expect(wrapper.get('[aria-label="Changelog"]').attributes("href")).toBe("/repos/devteam/bismark/shortlog")
    })
})

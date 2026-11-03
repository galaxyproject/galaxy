import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils"
import { afterEach, describe, expect, it } from "vitest"
import { createMemoryRouter } from "@/test-utils"
import RepositoryActions from "./RepositoryActions.vue"
import RepositoryExplore from "./RepositoryExplore.vue"
import RepositoryHealth from "./RepositoryHealth.vue"

const repository = { id: "abc", name: "bismark", owner: "devteam" }

enableAutoUnmount(afterEach)

function withRouter() {
    return { global: { plugins: [createMemoryRouter()] }, attachTo: document.body }
}

function menuItem(wrapper: VueWrapper, text: string) {
    const item = wrapper.findAll(".dropdown-item").find((candidate) => candidate.text() === text)
    if (!item) {
        throw new Error(`no "${text}" menu item`)
    }
    return item
}

describe("RepositoryHealth", () => {
    it("lists downloadability, installs and last update as readable facts", () => {
        const wrapper = mount(RepositoryHealth, {
            props: { downloadable: true, installs: 12, lastUpdated: new Date().toISOString().replace("Z", "") },
        })
        const pills = wrapper.findAll(".health-pill")

        expect(pills.map((pill) => pill.text())).toEqual([
            "Downloadable",
            "12 installs",
            expect.stringMatching(/^Updated .+ ago$/),
        ])
        expect(pills[0].classes()).toContain("health-ok")
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
        await menuItem(wrapper, "Mark as Deprecated").trigger("click")

        expect(wrapper.emitted("deprecate")).toEqual([[]])
    })

    it("offers to un-deprecate a deprecated repository", async () => {
        const wrapper = mount(RepositoryActions, { props: { repositoryId: "abc", deprecated: true }, ...withRouter() })

        await menuItem(wrapper, "Un-mark as Deprecated").trigger("click")

        expect(wrapper.emitted("undeprecate")).toEqual([[]])
        expect(wrapper.findAll(".dropdown-item").map((item) => item.text())).not.toContain("Mark as Deprecated")
    })
})

describe("RepositoryExplore", () => {
    it("links the changelog and contents from the explore menu", () => {
        const wrapper = mount(RepositoryExplore, { props: { repository }, ...withRouter() })

        const links = wrapper.findAll("a.dropdown-item").map((link) => link.attributes("href"))
        expect(links).toEqual(["/repos/devteam/bismark/shortlog", "/repos/devteam/bismark/file/tip"])
    })

    it("shows labelled icon buttons in dense mode, including the optional external links", () => {
        const wrapper = mount(RepositoryExplore, {
            props: {
                repository: { ...repository, homepage_url: "https://example.org", remote_repository_url: null },
                dense: true,
            },
            ...withRouter(),
        })

        const labels = wrapper.findAll(".repository-explore-buttons .g-button").map((b) => b.attributes("aria-label"))
        expect(labels).toEqual(["Details", "Metadata Inspector", "Changelog", "Contents", "Homepage"])
        expect(wrapper.get('[aria-label="Homepage"]').attributes("href")).toBe("https://example.org")
    })
})

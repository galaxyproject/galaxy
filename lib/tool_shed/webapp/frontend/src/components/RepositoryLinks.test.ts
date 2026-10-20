import { mount } from "@vue/test-utils"
import { describe, expect, it, vi } from "vitest"
import RepositoryLinks from "./RepositoryLinks.vue"

const { copyAndNotify } = vi.hoisted(() => ({ copyAndNotify: vi.fn() }))
vi.mock("@/util", () => ({ copyAndNotify }))

const repository = {
    id: "abc",
    name: "bismark",
    owner: "devteam",
    type: "unrestricted",
    description: "Bisulfite mapper",
    long_description: null,
    category_ids: [],
    user_id: "u1",
    private: false,
    deleted: false,
    deprecated: false,
    times_downloaded: 0,
    create_time: "2024-01-01T00:00:00",
    update_time: "2024-01-01T00:00:00",
}

function links(wrapper: ReturnType<typeof mount>) {
    return wrapper.findAll(".repository-link").map((link) => ({
        label: link.get(".repository-link-label").text(),
        href: link.find("a").exists() ? link.get("a").attributes("href") : null,
    }))
}

describe("RepositoryLinks", () => {
    it("links the revision's permalink, homepage and development repository", () => {
        const wrapper = mount(RepositoryLinks, {
            props: {
                repository: {
                    ...repository,
                    homepage_url: "https://example.org/bismark",
                    remote_repository_url: "https://github.com/devteam/bismark",
                },
                currentRevision: "abcdef123456",
            },
        })

        expect(links(wrapper)).toEqual([
            { label: "Permalink", href: "/view/devteam/bismark/abcdef123456" },
            { label: "Homepage", href: "https://example.org/bismark" },
            { label: "Development repository", href: "https://github.com/devteam/bismark" },
        ])
    })

    it("leaves out links the repository doesn't have", () => {
        const wrapper = mount(RepositoryLinks, { props: { repository, currentRevision: null } })

        expect(links(wrapper)).toEqual([])
    })

    it("gives the hg clone command, as hgweb pages may need a login but cloning doesn't", async () => {
        const wrapper = mount(RepositoryLinks, {
            props: {
                repository: { ...repository, clone_url: "https://toolshed.example/repos/devteam/bismark" },
                currentRevision: null,
            },
        })

        expect(links(wrapper)).toEqual([{ label: "Mercurial clone", href: null }])
        const command = "hg clone https://toolshed.example/repos/devteam/bismark"
        expect(wrapper.get(".repository-link code").text()).toBe(command)
        await wrapper.get("button[aria-label='Copy clone command']").trigger("click")
        expect(copyAndNotify).toHaveBeenCalledWith(command, "Clone command copied to your clipboard")
    })
})

import { describe, it, expect, beforeEach, vi } from "vitest"
import { type DOMWrapper, flushPromises, mount } from "@vue/test-utils"
import ToolVersionPage from "./ToolVersionPage.vue"

const getParsedTool = vi.fn()

vi.mock("@/api", () => ({
    getParsedTool: (...args: unknown[]) => getParsedTool(...args),
}))

function parsedTool(overrides: Record<string, unknown> = {}) {
    return {
        id: "cat1",
        name: "Concatenate",
        version: "1.0.0",
        description: "tail-to-head",
        license: "MIT",
        profile: null,
        edam_operations: ["operation_3436"],
        edam_topics: [],
        xrefs: [{ type: "bio.tools", value: "cat" }],
        citations: [],
        help: null,
        repository_revision: {
            changeset_revision: "abc123",
            repository: { owner: "devteam", name: "concat" },
        },
        ...overrides,
    }
}

async function mountPage() {
    const wrapper = mount(ToolVersionPage, {
        props: { trsToolId: "devteam~concat~cat1", version: "1.0.0" },
        global: {
            stubs: {
                // QPage renders nothing outside a QLayout
                QPage: { template: "<div><slot /></div>" },
                RouterLink: { props: ["to"], template: '<a :href="to"><slot /></a>' },
                LicenseLink: { props: ["id"], template: '<span class="stub-license">{{ id }}</span>' },
                EdamLink: { props: ["term"], template: '<span class="stub-edam">{{ term }}</span>' },
                BioToolsLink: { props: ["id"], template: '<span class="stub-biotools">{{ id }}</span>' },
                PreformattedContent: true,
            },
        },
    })
    await flushPromises()
    return wrapper
}

function detailPairs(list: DOMWrapper<Element>) {
    return list.findAll(".tool-detail").map((detail) => [detail.find("dt").text(), detail.find("dd").text()])
}

describe("ToolVersionPage", () => {
    beforeEach(() => {
        getParsedTool.mockReset()
    })

    it("shows the tool name as the page heading", async () => {
        getParsedTool.mockResolvedValue(parsedTool())
        const wrapper = await mountPage()

        expect(wrapper.find("h1").text()).toBe("Concatenate")
        expect(wrapper.text()).toContain("tail-to-head")
    })

    it("lists the tool's details as term/description pairs", async () => {
        getParsedTool.mockResolvedValue(parsedTool())
        const wrapper = await mountPage()

        const details = wrapper.findAll("dl.tool-details")
        expect(detailPairs(details[0])).toEqual([
            ["Repository", "devteam / concat (@ abc123)"],
            ["TRS ID", "devteam~concat~cat1"],
            ["LICENSE", "MIT"],
            ["PROFILE", "no profile specified - default of 16.01 assumed"],
            ["EDAM OPERATION", "operation_3436"],
        ])
        expect(details[0].find("a").attributes("href")).toBe("/view/devteam/concat/abc123")
        expect(detailPairs(details[1])).toEqual([["Catalog bio.tools", "cat"]])
    })

    it("lists citations when the tool has them", async () => {
        getParsedTool.mockResolvedValue(parsedTool({ citations: [{ type: "doi", content: "10.1000/xyz" }] }))
        const wrapper = await mountPage()

        const details = wrapper.findAll("dl.tool-details")
        expect(detailPairs(details[details.length - 1])).toEqual([["doi", "10.1000/xyz"]])
    })

    it("says so when the tool defines no references", async () => {
        getParsedTool.mockResolvedValue(parsedTool({ xrefs: [] }))
        const wrapper = await mountPage()

        expect(wrapper.findAll("dl.tool-details").length).toBe(1)
        expect(wrapper.text()).toContain("This tool does not define any references.")
    })
})

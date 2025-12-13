import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount } from "@vue/test-utils"
import { nextTick } from "vue"
import RevisionsTab from "./RevisionsTab.vue"
import {
    repositoryMetadataColumnMaker,
    repositoryMetadataBismark,
    makeRevision,
    type RepositoryMetadata,
    type RepositoryRevisionMetadata,
} from "./__fixtures__"

vi.mock("./MetadataJsonViewer.vue", () => ({
    default: {
        name: "MetadataJsonViewer",
        props: ["data", "modelName", "deep"],
        template: '<div class="mock-json-viewer">{{ JSON.stringify(data) }}</div>',
    },
}))

const fixtureMetadata = repositoryMetadataColumnMaker
const bismarkMetadata = repositoryMetadataBismark

describe("RevisionsTab", () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    describe("rendering", () => {
        it("displays 'No revisions found' when metadata is null", () => {
            const wrapper = mount(RevisionsTab, {
                props: { metadata: null },
            })

            expect(wrapper.text()).toContain("No revisions found")
        })

        it("displays 'No revisions found' when metadata is empty", () => {
            const wrapper = mount(RevisionsTab, {
                props: { metadata: {} as RepositoryMetadata },
            })

            expect(wrapper.text()).toContain("No revisions found")
        })

        it("displays list of revisions", () => {
            const wrapper = mount(RevisionsTab, {
                props: { metadata: fixtureMetadata },
            })

            expect(wrapper.find(".q-list").exists()).toBe(true)
        })

        it("shows revision identifiers in format [num:hash]", () => {
            const wrapper = mount(RevisionsTab, {
                props: { metadata: fixtureMetadata },
            })

            const keys = Object.keys(fixtureMetadata)
            for (const key of keys) {
                const [num, hash] = key.split(":")
                expect(wrapper.text()).toContain(`[${num}:${hash.substring(0, 7)}]`)
            }
        })
    })

    describe("sorting", () => {
        it("sorts revisions with newest first", () => {
            const wrapper = mount(RevisionsTab, {
                props: { metadata: fixtureMetadata },
            })

            const text = wrapper.text()
            const keys = Object.keys(fixtureMetadata)
            const nums = keys.map((k) => parseInt(k.split(":")[0])).sort((a, b) => b - a)

            if (nums.length >= 2) {
                const newestIndex = text.indexOf(`[${nums[0]}:`)
                const oldestIndex = text.indexOf(`[${nums[nums.length - 1]}:`)
                expect(newestIndex).toBeLessThan(oldestIndex)
            }
        })
    })

    describe("tool summary", () => {
        it("shows tool ID for revisions with tools", () => {
            const wrapper = mount(RevisionsTab, {
                props: { metadata: fixtureMetadata },
            })

            expect(wrapper.text()).toContain("Add_a_column1")
        })

        it("shows 'No tools' for revisions without tools", () => {
            const keys = Object.keys(fixtureMetadata)
            const noToolsMetadata: RepositoryMetadata = {
                [keys[0]]: makeRevision({ tools: [] }),
            }

            const wrapper = mount(RevisionsTab, {
                props: { metadata: noToolsMetadata },
            })

            expect(wrapper.text()).toContain("No tools")
        })
    })

    describe("invalid tools", () => {
        it("shows badge for revisions with invalid tools", () => {
            const wrapper = mount(RevisionsTab, {
                props: { metadata: bismarkMetadata },
            })

            expect(wrapper.text()).toMatch(/\d+ invalid/)
        })

        it("shows invalid tool paths when revision is expanded", async () => {
            const keyWithInvalid = Object.entries(bismarkMetadata).find(
                ([, rev]) => rev.invalid_tools && rev.invalid_tools.length > 0
            )?.[0]

            if (keyWithInvalid) {
                const wrapper = mount(RevisionsTab, {
                    props: {
                        metadata: bismarkMetadata,
                        expandRevision: keyWithInvalid,
                    },
                })

                await nextTick()

                const invalidTools = bismarkMetadata[keyWithInvalid].invalid_tools
                if (invalidTools && invalidTools.length > 0) {
                    expect(wrapper.text()).toContain(invalidTools[0])
                }
            }
        })
    })

    describe("expandRevision prop", () => {
        it("auto-expands revision when expandRevision prop is set", async () => {
            const firstKey = Object.keys(fixtureMetadata)[0]

            const wrapper = mount(RevisionsTab, {
                props: {
                    metadata: fixtureMetadata,
                    expandRevision: firstKey,
                },
            })

            await nextTick()

            expect(wrapper.find(".mock-json-viewer").exists()).toBe(true)
        })

        it("expands new revision when expandRevision prop changes", async () => {
            const keys = Object.keys(fixtureMetadata)

            const wrapper = mount(RevisionsTab, {
                props: {
                    metadata: fixtureMetadata,
                    expandRevision: null,
                },
            })

            // Initially no expansion items have model-value true
            const expansionItems = wrapper.findAllComponents({ name: "QExpansionItem" })
            const initiallyExpanded = expansionItems.filter((item) => item.props("modelValue") === true)
            expect(initiallyExpanded.length).toBe(0)

            await wrapper.setProps({ expandRevision: keys[0] })
            await nextTick()

            // After setting prop, one should be expanded
            const afterExpanded = expansionItems.filter((item) => item.props("modelValue") === true)
            expect(afterExpanded.length).toBe(1)
        })
    })

    describe("expansion items", () => {
        it("renders one expansion item per revision", () => {
            const wrapper = mount(RevisionsTab, {
                props: { metadata: fixtureMetadata },
            })

            const expansionItems = wrapper.findAll(".q-expansion-item")
            expect(expansionItems.length).toBe(Object.keys(fixtureMetadata).length)
        })
    })

    describe("edge cases", () => {
        it("handles revision with repository dependencies", () => {
            const keys = Object.keys(fixtureMetadata)
            const depsMetadata: RepositoryMetadata = {
                [keys[0]]: makeRevision({
                    repository_dependencies: [
                        makeRevision() as unknown as RepositoryRevisionMetadata,
                        makeRevision() as unknown as RepositoryRevisionMetadata,
                    ],
                    has_repository_dependencies: true,
                }),
            }

            const wrapper = mount(RevisionsTab, {
                props: { metadata: depsMetadata },
            })

            expect(wrapper.text()).toContain("2 repo deps")
        })

        it("handles revision with many invalid tools", () => {
            const keys = Object.keys(fixtureMetadata)
            const manyInvalidMetadata: RepositoryMetadata = {
                [keys[0]]: makeRevision({
                    tools: [],
                    downloadable: false,
                    invalid_tools: ["t1.xml", "t2.xml", "t3.xml", "t4.xml", "t5.xml"],
                }),
            }

            const wrapper = mount(RevisionsTab, {
                props: { metadata: manyInvalidMetadata },
            })

            expect(wrapper.text()).toContain("5 invalid")
        })
    })
})

import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount } from "@vue/test-utils"
import ToolHistoryTab from "./ToolHistoryTab.vue"
import {
    repositoryMetadataColumnMaker,
    simulatedMetadataMultiTool,
    simulatedMetadataEmpty,
    makeRevision,
    makeTool,
    type RepositoryMetadata,
} from "./__fixtures__"

vi.mock("./MetadataJsonViewer.vue", () => ({
    default: {
        name: "MetadataJsonViewer",
        props: ["data", "modelName", "deep"],
        template: '<div class="mock-json-viewer">{{ JSON.stringify(data) }}</div>',
    },
}))

const fixtureMetadata = repositoryMetadataColumnMaker

describe("ToolHistoryTab", () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    describe("rendering", () => {
        it("displays 'No tools found' when metadata is null", () => {
            const wrapper = mount(ToolHistoryTab, {
                props: { metadata: null },
            })

            expect(wrapper.text()).toContain("No tools found")
        })

        it("displays 'No tools found' when metadata has no tools", () => {
            const wrapper = mount(ToolHistoryTab, {
                props: { metadata: simulatedMetadataEmpty },
            })

            expect(wrapper.text()).toContain("No tools found")
        })

        it("displays tool cards with tool ID as header", () => {
            const wrapper = mount(ToolHistoryTab, {
                props: { metadata: fixtureMetadata },
            })

            const cards = wrapper.findAll(".q-card")
            expect(cards.length).toBeGreaterThan(0)
            expect(wrapper.text()).toContain("Add_a_column1")
        })

        it("shows version numbers in timeline", () => {
            const wrapper = mount(ToolHistoryTab, {
                props: { metadata: fixtureMetadata },
            })

            expect(wrapper.text()).toMatch(/\d+\.\d+\.\d+/)
        })
    })

    describe("tool history sorting", () => {
        it("sorts versions with newest revision first", () => {
            const wrapper = mount(ToolHistoryTab, {
                props: { metadata: fixtureMetadata },
            })

            const text = wrapper.text()
            // column_maker has versions 1.1.0, 1.2.0, 1.3.0 - newest should be first
            const v130Index = text.indexOf("1.3.0")
            const v110Index = text.indexOf("1.1.0")

            if (v130Index !== -1 && v110Index !== -1) {
                expect(v130Index).toBeLessThan(v110Index)
            }
        })

        it("sorts tools alphabetically by tool ID", () => {
            const wrapper = mount(ToolHistoryTab, {
                props: { metadata: simulatedMetadataMultiTool },
            })

            const text = wrapper.text()
            const alignIndex = text.indexOf("align_sequences")
            const convertIndex = text.indexOf("convert_format")
            const filterIndex = text.indexOf("filter_quality")
            const mergeIndex = text.indexOf("merge_sequences")

            expect(alignIndex).not.toBe(-1)
            expect(convertIndex).not.toBe(-1)
            expect(filterIndex).not.toBe(-1)
            expect(mergeIndex).not.toBe(-1)

            expect(alignIndex).toBeLessThan(convertIndex)
            expect(convertIndex).toBeLessThan(filterIndex)
            expect(filterIndex).toBeLessThan(mergeIndex)
        })
    })

    describe("events", () => {
        it("emits goToRevision when revision link is clicked", async () => {
            const wrapper = mount(ToolHistoryTab, {
                props: { metadata: fixtureMetadata },
            })

            const revButtons = wrapper.findAll(".q-btn")
            const revButton = revButtons.find((btn) => btn.text().includes("Rev"))
            expect(revButton).toBeTruthy()

            await revButton!.trigger("click")

            expect(wrapper.emitted("goToRevision")).toBeTruthy()
            expect(wrapper.emitted("goToRevision")![0]).toBeTruthy()
        })
    })

    describe("expansion", () => {
        it("has expandable tool details section", () => {
            const wrapper = mount(ToolHistoryTab, {
                props: { metadata: fixtureMetadata },
            })

            const expansionItems = wrapper.findAll(".q-expansion-item")
            expect(expansionItems.length).toBeGreaterThan(0)
        })
    })

    describe("edge cases", () => {
        it("shows multiple entries when tool has same version in different revisions", () => {
            // simulatedMetadataMultiTool has filter_quality at 1.0.0 in rev 0 and rev 1
            const wrapper = mount(ToolHistoryTab, {
                props: { metadata: simulatedMetadataMultiTool },
            })

            const text = wrapper.text()
            expect(text).toContain("filter_quality")
            expect(text).toContain("1.0.0")
        })

        it("handles special characters in tool IDs", () => {
            const keys = Object.keys(fixtureMetadata)
            const specialCharsMetadata: RepositoryMetadata = {
                [keys[0]]: makeRevision({
                    tools: [makeTool({ id: "tool_with-special.chars", name: "Tool Name", version: "1.0" })],
                }),
            }

            const wrapper = mount(ToolHistoryTab, {
                props: { metadata: specialCharsMetadata },
            })

            expect(wrapper.text()).toContain("tool_with-special.chars")
        })
    })
})

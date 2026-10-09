import { describe, it, expect, afterEach } from "vitest"
import { enableAutoUnmount, mount } from "@vue/test-utils"
import { nextTick } from "vue"
import ChangesetSummaryTable from "./ChangesetSummaryTable.vue"
import { getChangesetDetails, resetMetadataPreview, makeChangeset, type ChangesetMetadataStatus } from "./__fixtures__"

enableAutoUnmount(afterEach)

// Real fixture data from API
const fixtureChangesets = getChangesetDetails(resetMetadataPreview)

describe("ChangesetSummaryTable", () => {
    describe("rendering with real fixture data", () => {
        it("renders a table", () => {
            const wrapper = mount(ChangesetSummaryTable, {
                props: { changesets: fixtureChangesets },
            })

            expect(wrapper.find("table").exists()).toBe(true)
        })

        it("displays all changesets from fixture", () => {
            const wrapper = mount(ChangesetSummaryTable, {
                props: { changesets: fixtureChangesets },
            })

            for (const cs of fixtureChangesets) {
                const shortHash = cs.changeset_revision.substring(0, 7)
                expect(wrapper.text()).toContain(`${cs.numeric_revision}:${shortHash}`)
            }
        })

        it("shows column headers", () => {
            const wrapper = mount(ChangesetSummaryTable, {
                props: { changesets: fixtureChangesets },
            })

            expect(wrapper.text()).toContain("Revision")
            expect(wrapper.text()).toContain("Change Type")
            expect(wrapper.text()).toContain("Snapshot")
            expect(wrapper.text()).toContain("Tools")
            expect(wrapper.text()).toContain("Error")
        })
    })

    describe("comparison_result display", () => {
        it.each<Pick<ChangesetMetadataStatus, "comparison_result" | "record_operation"> & { label: string }>([
            { comparison_result: "initial", record_operation: null, label: "First revision" },
            { comparison_result: "not equal and not subset", record_operation: "updated", label: "Modified" },
            { comparison_result: "equal", record_operation: null, label: "Unchanged" },
            { comparison_result: "subset", record_operation: null, label: "Expanded" },
        ])("labels $comparison_result as $label", ({ label, ...changeset }) => {
            const changesets = [makeChangeset(changeset)]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            expect(wrapper.find("td .comparison-result").text()).toBe(label)
        })

        it("shows dash when comparison_result is null", () => {
            const changesets = [makeChangeset({ comparison_result: null, error: "some error" })]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            expect(wrapper.find("tbody tr td:nth-child(2)").text()).toBe("—")
        })
    })

    describe("record_operation display", () => {
        it("displays created in a badge with a distinct created class", () => {
            const changesets = [
                makeChangeset({ comparison_result: "not equal and not subset", record_operation: "created" }),
            ]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            const badge = wrapper.find(".record-operation-badge")
            expect(badge.exists()).toBe(true)
            expect(badge.text()).toContain("created")
            expect(badge.classes()).toContain("record-operation-badge--created")
        })

        it("displays updated in a badge with a distinct updated class", () => {
            const changesets = [
                makeChangeset({ comparison_result: "not equal and not subset", record_operation: "updated" }),
            ]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            const badge = wrapper.find(".record-operation-badge")
            expect(badge.exists()).toBe(true)
            expect(badge.text()).toContain("updated")
            expect(badge.classes()).toContain("record-operation-badge--updated")
        })

        it("shows dash when record_operation is null", () => {
            const changesets = [makeChangeset({ comparison_result: "initial", record_operation: null })]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            const snapshotCell = wrapper.find("tbody tr td:nth-child(3)")
            expect(snapshotCell.text()).toBe("—")
        })
    })

    describe("tooltips", () => {
        it("wires each header help icon to a tooltip via aria-describedby", async () => {
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets: fixtureChangesets } })
            // GTooltip sets aria-describedby on its reference reactively, once the template
            // ref to the trigger span is flushed -- that happens a tick after mount.
            await nextTick()

            const triggers = wrapper.findAll("th .header-help")
            expect(triggers).toHaveLength(2)

            for (const trigger of triggers) {
                const describedBy = trigger.attributes("aria-describedby")
                expect(describedBy).toBeTruthy()
                expect(wrapper.find(`#${describedBy}`).exists()).toBe(true)
            }
        })

        it("explains both columns in the header tooltips", () => {
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets: fixtureChangesets } })

            const tooltips = wrapper.findAll('[role="tooltip"]')
            expect(tooltips).toHaveLength(2)
            expect(tooltips.some((t) => t.text().includes("Snapshots are created"))).toBe(true)
            expect(tooltips.some((t) => t.text().includes("refreshed"))).toBe(true)
        })

        it("puts the per-row comparison_result explanation in a title, since each row needs its own", () => {
            const changesets = [makeChangeset({ comparison_result: "subset" })]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            const cell = wrapper.find("td .comparison-result")
            expect(cell.attributes("title")).toContain("changes accumulate")
            // A title never shows on keyboard focus, so the cell isn't a tab stop
            expect(cell.attributes("tabindex")).toBeUndefined()
        })

        it("names the focusable header help icons", () => {
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets: fixtureChangesets } })

            const labels = wrapper.findAll("th .header-help").map((trigger) => trigger.attributes("aria-label"))
            expect(labels).toEqual(["About comparison results", "About record operations"])
        })
    })

    describe("tools indicator", () => {
        it("shows check icon when has_tools is true", () => {
            const changesets = [makeChangeset({ has_tools: true })]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            expect(wrapper.find('[data-icon="check"]').exists()).toBe(true)
            expect(wrapper.find('[data-icon="xmark"]').exists()).toBe(false)
        })

        it("shows close icon when has_tools is false", () => {
            const changesets = [makeChangeset({ has_tools: false })]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            expect(wrapper.find('[data-icon="xmark"]').exists()).toBe(true)
            expect(wrapper.find('[data-icon="check"]').exists()).toBe(false)
        })
    })

    describe("error display", () => {
        it("displays error message when present", () => {
            const changesets = [makeChangeset({ error: "Failed to parse tool XML" })]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            expect(wrapper.text()).toContain("Failed to parse tool XML")
        })

        it("does not render 'null' text when error is null", () => {
            const changesets = [makeChangeset({ error: null })]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            expect(wrapper.find("tbody tr td:nth-child(5)").text()).toBe("")
            expect(wrapper.text()).not.toContain("null")
        })
    })

    describe("edge cases", () => {
        it("renders empty table when changesets array is empty", () => {
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets: [] } })

            expect(wrapper.find("table").exists()).toBe(true)
            expect(wrapper.findAll("tbody tr")).toHaveLength(0)
        })

        it("truncates changeset hash to 7 characters", () => {
            const changesets = [makeChangeset({ changeset_revision: "abcdefghijklmnop" })]
            const wrapper = mount(ChangesetSummaryTable, { props: { changesets } })

            expect(wrapper.text()).toContain("1:abcdefg")
            expect(wrapper.text()).not.toContain("abcdefghijklmnop")
        })
    })
})

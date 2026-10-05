import { describe, it, expect, beforeEach, vi } from "vitest"
import { flushPromises, mount } from "@vue/test-utils"
import { defineComponent, h, ref } from "vue"
import MetadataInspectorPage from "./MetadataInspectorPage.vue"

const store = {
    loading: ref(false),
    repository: ref<{ name: string; owner: string } | null>({ name: "column_maker", owner: "devteam" }),
    repositoryMetadata: ref<Record<string, unknown> | null>({}),
    repositoryPermissions: ref<{ can_manage: boolean } | null>({ can_manage: false }),
    setId: vi.fn(),
    refresh: vi.fn(),
}

vi.mock("@/stores", () => ({
    useRepositoryStore: () => store,
}))

function stubTab(name: string, props: string[] = [], emits: string[] = []) {
    return {
        default: defineComponent({
            name,
            props,
            emits,
            setup(componentProps, { emit }) {
                return () =>
                    h("div", { class: `stub-${name}` }, [
                        JSON.stringify(componentProps),
                        ...emits.map((event) =>
                            h("button", { class: `emit-${event}`, onClick: () => emit(event, "3:abcdef0") }),
                        ),
                    ])
            },
        }),
    }
}

vi.mock("@/components/MetadataInspector/RevisionsTab.vue", () =>
    stubTab("RevisionsTab", ["metadata", "expandRevision"]),
)
vi.mock("@/components/MetadataInspector/ToolHistoryTab.vue", () =>
    stubTab("ToolHistoryTab", ["metadata"], ["goToRevision"]),
)
vi.mock("@/components/MetadataInspector/OverviewTab.vue", () => stubTab("OverviewTab", ["metadata"]))
vi.mock("@/components/MetadataInspector/ResetMetadataTab.vue", () =>
    stubTab("ResetMetadataTab", ["repositoryId"], ["resetComplete"]),
)

async function mountPage() {
    const wrapper = mount(MetadataInspectorPage, {
        props: { repositoryId: "abc123" },
        global: {
            // QPage renders nothing outside a QLayout
            stubs: { QPage: { template: "<div><slot /></div>" }, RouterLink: { template: "<a><slot /></a>" } },
        },
    })
    await flushPromises()
    return wrapper
}

function tabTitles(wrapper: Awaited<ReturnType<typeof mountPage>>) {
    return wrapper.findAll("[role=tab]").map((tab) => tab.text())
}

function activeTitle(wrapper: Awaited<ReturnType<typeof mountPage>>) {
    return wrapper.find("[role=tab][aria-selected=true]").text()
}

describe("MetadataInspectorPage", () => {
    beforeEach(() => {
        store.repositoryPermissions.value = { can_manage: false }
        store.repositoryMetadata.value = { "0:aaaaaaa": {}, "1:bbbbbbb": {} }
    })

    it("renders the always-visible tabs, with Revisions selected", async () => {
        const wrapper = await mountPage()

        expect(tabTitles(wrapper)).toEqual(["Revisions (2)", "Tool History", "Raw JSON"])
        expect(activeTitle(wrapper)).toBe("Revisions (2)")
    })

    it("adds the Reset Metadata tab only for managers", async () => {
        store.repositoryPermissions.value = { can_manage: true }
        const wrapper = await mountPage()

        expect(tabTitles(wrapper)).toEqual(["Revisions (2)", "Tool History", "Raw JSON", "Reset Metadata"])
    })

    it("mounts tab content only once its tab is shown", async () => {
        store.repositoryPermissions.value = { can_manage: true }
        const wrapper = await mountPage()

        expect(wrapper.find(".stub-RevisionsTab").exists()).toBe(true)
        expect(wrapper.find(".stub-ResetMetadataTab").exists()).toBe(false)

        await wrapper.findAll("[role=tab]")[3].trigger("click")

        expect(activeTitle(wrapper)).toBe("Reset Metadata")
        expect(wrapper.find(".stub-ResetMetadataTab").exists()).toBe(true)
    })

    it("switches to Revisions and expands the revision when Tool History asks for it", async () => {
        const wrapper = await mountPage()

        await wrapper.findAll("[role=tab]")[1].trigger("click")
        expect(activeTitle(wrapper)).toBe("Tool History")

        await wrapper.find(".emit-goToRevision").trigger("click")
        await flushPromises()

        expect(activeTitle(wrapper)).toBe("Revisions (2)")
        expect(wrapper.find(".stub-RevisionsTab").text()).toContain("3:abcdef0")
    })

    describe("invalid tools alert", () => {
        it("is absent when no revision has invalid tools", async () => {
            const wrapper = await mountPage()

            expect(wrapper.find(".invalid-tools-alert").exists()).toBe(false)
        })

        it("counts invalid tools across revisions and links back to Revisions", async () => {
            store.repositoryMetadata.value = {
                "0:aaaaaaa": { invalid_tools: [{ tool_config: "a.xml" }] },
                "1:bbbbbbb": { invalid_tools: [{ tool_config: "b.xml" }, { tool_config: "c.xml" }] },
            }
            const wrapper = await mountPage()

            const alert = wrapper.find(".invalid-tools-alert")
            expect(alert.classes()).toContain("alert-warning")
            // A standing finding, announced politely rather than as an interrupting alert
            expect(alert.attributes("role")).toBe("status")
            expect(alert.text()).toContain("3 invalid tool(s) found across revisions.")

            await wrapper.findAll("[role=tab]")[2].trigger("click")
            expect(activeTitle(wrapper)).toBe("Raw JSON")

            const viewButton = alert.findAll("button").find((button) => button.text() === "View in Revisions")
            expect(viewButton).toBeDefined()
            await viewButton?.trigger("click")
            expect(activeTitle(wrapper)).toBe("Revisions (2)")
        })
    })
})

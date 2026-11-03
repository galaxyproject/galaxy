import { createTestingPinia, type TestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getFakeWorkflowSummary } from "@tests/test-data/workflows";
import { deferred } from "@tests/vitest/deferred";
import {
    createTestRouter,
    expectConfigurationRequest,
    getLocalVue,
    suppressBootstrapVueWarnings,
    withPlugins,
} from "@tests/vitest/helpers";
import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { loadWorkflows, type WorkflowSummary } from "@/api/workflows";
import { raisedToasts } from "@/composables/__mocks__/toast";
import { useUserStore } from "@/stores/userStore";

import WorkflowCardList from "./WorkflowCardList.vue";
import WorkflowList from "./WorkflowList.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const { server, http } = useServerMock();

const { confirm } = vi.hoisted(() => ({ confirm: vi.fn() }));

vi.mock("@/api/workflows", async (importOriginal) => ({
    ...(await importOriginal<object>()),
    loadWorkflows: vi.fn(),
}));
vi.mock("@/composables/confirmDialog", () => ({
    useConfirmDialog: () => ({ confirm }),
}));
vi.mock("@/composables/toast");

const mockedLoadWorkflows = vi.mocked(loadWorkflows);

const localVue = getLocalVue();
const router = createTestRouter();

const FAKE_USERNAME = "fake_username";
const FAKE_USER = getFakeRegisteredUser({
    id: "fake_user_id",
    email: "fake_user_email",
    username: FAKE_USERNAME,
});

const SELECTORS = {
    WORKFLOW_CARD: ".workflow-card",
    EMPTY_LIST: "#workflow-list-empty",
    FILTER_INPUT: "#workflow-list-filter input",
    SHOW_DELETED_BUTTON: "#show-deleted",
    CARD_DESCRIPTION: ".g-card-description",
    CARD_TAGS: ".stateless-tags",
    TAG: ".tag",
    SHOW_MORE_TAGS: ".show-more-tags",
    BULK_UNSHARE_BUTTON: "#workflow-list-footer-bulk-unshare-button",
    BULK_DELETE_BUTTON: "#workflow-list-footer-bulk-delete-button",
    BULK_ADD_TAGS_BUTTON: "#workflow-list-footer-bulk-add-tags-button",
};

type ActiveList = "my" | "shared_with_me";
type WorkflowListPage = Awaited<ReturnType<typeof loadWorkflows>>;

/** Serves the given workflows as the list's only page. */
function serveWorkflowList(workflows: WorkflowSummary[]) {
    mockedLoadWorkflows.mockResolvedValue({ data: workflows, totalMatches: workflows.length });
    return workflows;
}

/** Workflows owned by the fake user. */
function ownWorkflows(count: number, overrides: Partial<WorkflowSummary> = {}, idPrefix = "workflow") {
    return Array.from({ length: count }, (_, i) =>
        getFakeWorkflowSummary({ id: `${idPrefix}-${i}`, name: `Workflow ${i}`, owner: FAKE_USERNAME, ...overrides }),
    );
}

/** Workflows owned by the fake user, served as the list's only page. */
function serveWorkflows(count: number, overrides: Partial<WorkflowSummary> = {}) {
    return serveWorkflowList(ownWorkflows(count, overrides));
}

/** Mounts the list before any user has loaded; the "my" list waits for one. */
function mountWorkflowList({
    pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false }),
    activeList = "my",
}: { pinia?: TestingPinia; activeList?: ActiveList } = {}) {
    setActivePinia(pinia);
    const wrapper = mount(WorkflowList, { props: { activeList }, global: withPlugins(localVue, pinia, router) });
    return { wrapper, userStore: useUserStore() };
}

async function mountWorkflowListForUser(activeList: ActiveList = "my") {
    const { wrapper, userStore } = mountWorkflowList({ activeList });
    userStore.currentUser = FAKE_USER;
    await flushPromises();
    return wrapper;
}

function filterText(wrapper: VueWrapper) {
    return wrapper.find<HTMLInputElement>(SELECTORS.FILTER_INPUT).element.value;
}

function deleteKeyEvent(): KeyboardEvent {
    const target = document.createElement("div");
    target.classList.add("workflow-card-in-list");
    return { key: "Delete", shiftKey: false, target, preventDefault: () => {} } as unknown as KeyboardEvent;
}

enableAutoUnmount(afterEach);

describe("WorkflowList", () => {
    beforeEach(() => {
        suppressBootstrapVueWarnings();
        vi.clearAllMocks();
        server.use(
            // Workflow card badges request their counts.
            http.get("/api/workflows/{workflow_id}/counts", ({ response }) => {
                return response(200).json({});
            }),
            // The tab bar reads useConfig(), and the configuration store fetches in its setup body.
            expectConfigurationRequest(http, {}),
        );
    });

    it("shows the empty-list message when there are no workflows", async () => {
        serveWorkflows(0);
        const wrapper = await mountWorkflowListForUser();

        expect(wrapper.findAll(SELECTORS.WORKFLOW_CARD)).toHaveLength(0);
        expect(wrapper.find(SELECTORS.EMPTY_LIST).exists()).toBe(true);
    });

    it("renders a card for each workflow", async () => {
        const workflows = serveWorkflows(10);
        const wrapper = await mountWorkflowListForUser();

        expect(wrapper.findAll(SELECTORS.WORKFLOW_CARD)).toHaveLength(10);
        expect(wrapper.find(SELECTORS.EMPTY_LIST).exists()).toBe(false);

        const nonDeletedWorkflows = workflows.filter((w) => !w.deleted);
        expect(wrapper.findAll(SELECTORS.WORKFLOW_CARD)).toHaveLength(nonDeletedWorkflows.length);
    });

    it("shows each workflow's description, tags, bookmark and source on its card", async () => {
        serveWorkflowList([
            getFakeWorkflowSummary({
                id: "published-workflow",
                owner: FAKE_USERNAME,
                published: true,
                importable: true,
                annotations: ["Aligns paired-end reads"],
                tags: ["name:paired", "rna-seq", "alignment"],
                show_in_tool_panel: true,
            }),
            getFakeWorkflowSummary({
                id: "imported-workflow",
                owner: FAKE_USERNAME,
                source_metadata: { url: "https://example.org/imported.ga" },
            }),
        ]);
        const wrapper = await mountWorkflowListForUser();

        const publishedCard = wrapper.get("#g-card-published-workflow");
        expect(publishedCard.get(SELECTORS.CARD_DESCRIPTION).text()).toBe("Aligns paired-end reads");
        // The default grid view shows two tags per card.
        expect(publishedCard.findAll(SELECTORS.TAG).map((tag) => tag.text())).toEqual(["#paired", "rna-seq"]);
        expect(publishedCard.get(SELECTORS.SHOW_MORE_TAGS).text()).toBe("1 more...");
        expect(publishedCard.find("[title='Remove bookmark']").exists()).toBe(true);
        expect(publishedCard.find("[title='Published workflow. Click to filter published workflows']").exists()).toBe(
            true,
        );

        await publishedCard.get(SELECTORS.SHOW_MORE_TAGS).trigger("click");
        expect(publishedCard.findAll(SELECTORS.TAG).map((tag) => tag.text())).toEqual([
            "#paired",
            "rna-seq",
            "alignment",
        ]);

        const importedCard = wrapper.get("#g-card-imported-workflow");
        expect(importedCard.get(SELECTORS.CARD_DESCRIPTION).text()).toBe("");
        expect(importedCard.findAll(SELECTORS.TAG)).toHaveLength(0);
        expect(importedCard.find("[title='Add to bookmarks']").exists()).toBe(true);
        expect(importedCard.find("[title^='Published workflow']").exists()).toBe(false);
        expect(
            importedCard.find("[title='Imported from https://example.org/imported.ga. Click to copy link']").exists(),
        ).toBe(true);
    });

    it("shows deleted workflows' tags read-only", async () => {
        serveWorkflowList([
            getFakeWorkflowSummary({
                id: "deleted-workflow",
                owner: FAKE_USERNAME,
                deleted: true,
                tags: ["name:archived", "legacy", "unused"],
            }),
        ]);
        const wrapper = await mountWorkflowListForUser();

        const deletedCard = wrapper.get("#g-card-deleted-workflow");
        const tags = deletedCard.get(SELECTORS.CARD_TAGS);
        expect(tags.findAll(".d-inline > .tag").map((tag) => tag.text())).toEqual(["#archived", "legacy"]);
        expect(tags.find(".tag-delete-button").exists()).toBe(false);
        const showMoreButton = tags.get("button.toggle-link");
        expect(showMoreButton.text()).toBe("1 more...");
        // The hidden tags are listed in the button's tooltip.
        expect(tags.get(`#${showMoreButton.attributes("aria-describedby")}`).text()).toBe("unused");
    });

    it("renders own workflows when the user loads after the workflow list", async () => {
        serveWorkflows(3);
        const { wrapper, userStore } = mountWorkflowList({ pinia: createTestingPinia({ createSpy: vi.fn }) });
        await flushPromises();

        expect(wrapper.findAll(SELECTORS.WORKFLOW_CARD)).toHaveLength(0);
        expect(wrapper.findComponent(LoadingSpan).exists()).toBe(true);
        expect(wrapper.find(SELECTORS.EMPTY_LIST).exists()).toBe(false);

        userStore.currentUser = FAKE_USER;
        await flushPromises();

        expect(wrapper.findAll(SELECTORS.WORKFLOW_CARD)).toHaveLength(3);
        expect(wrapper.findComponent(LoadingSpan).exists()).toBe(false);
    });

    it("toggles the is:deleted filter with the show-deleted button", async () => {
        serveWorkflows(10, { deleted: true });
        const wrapper = await mountWorkflowListForUser();

        expect(filterText(wrapper)).toBe("");
        expect(wrapper.find(SELECTORS.SHOW_DELETED_BUTTON).exists()).toBe(true);

        await wrapper.find(SELECTORS.SHOW_DELETED_BUTTON).trigger("click");

        expect(filterText(wrapper)).toBe("is:deleted");
        expect(wrapper.find(SELECTORS.SHOW_DELETED_BUTTON).exists()).toBe(true);

        await wrapper.find(SELECTORS.SHOW_DELETED_BUTTON).trigger("click");

        expect(filterText(wrapper)).toBe("");
    });

    it("asks to delete on the Delete key in my view", async () => {
        const [workflow] = serveWorkflows(1);
        confirm.mockResolvedValue(false);
        const wrapper = await mountWorkflowListForUser("my");

        wrapper.findComponent(WorkflowCardList).vm.$emit("on-key-down", workflow, deleteKeyEvent());
        await flushPromises();

        expect(confirm).toHaveBeenCalledTimes(1);
        expect(confirm.mock.calls[0]?.[1]).toMatchObject({ title: "Delete workflow" });
    });

    describe("shared with me", () => {
        /** Two unpublished workflows another user shared, served as the list's only page. */
        function serveSharedWorkflows() {
            return serveWorkflowList(
                [1, 2].map((n) =>
                    getFakeWorkflowSummary({
                        id: `shared-${n}`,
                        name: `Shared ${n}`,
                        owner: "other_user",
                        published: false,
                    }),
                ),
            );
        }

        async function selectCards(wrapper: VueWrapper, workflows: WorkflowSummary[]) {
            for (const { id } of workflows) {
                await wrapper.find(`#g-card-select-${id}`).setValue(true);
            }
            await flushPromises();
        }

        /** Records each unshare request, failing the one for `failId`. */
        function interceptUnshare(failId?: string) {
            const unshared: string[] = [];
            server.use(
                http.put("/api/workflows/{workflow_id}/unshare_with_me", ({ params, response }) => {
                    unshared.push(params.workflow_id);
                    if (params.workflow_id === failId) {
                        return response("4XX").json({ err_msg: "Workflow not found", err_code: 404 }, { status: 404 });
                    }
                    return response(204).empty();
                }),
            );
            return unshared;
        }

        it("offers only Remove from Shared for selected shared workflows", async () => {
            const workflows = serveSharedWorkflows();
            const wrapper = await mountWorkflowListForUser("shared_with_me");

            await selectCards(wrapper, workflows);

            expect(wrapper.find(SELECTORS.BULK_UNSHARE_BUTTON).text()).toContain("Remove from Shared (2)");
            expect(wrapper.find(SELECTORS.BULK_DELETE_BUTTON).exists()).toBe(false);
            expect(wrapper.find(SELECTORS.BULK_ADD_TAGS_BUTTON).exists()).toBe(false);
        });

        it("removes every selected share once confirmed and refreshes", async () => {
            const workflows = serveSharedWorkflows();
            const unshared = interceptUnshare();
            confirm.mockResolvedValue(true);
            const wrapper = await mountWorkflowListForUser("shared_with_me");
            await selectCards(wrapper, workflows);
            mockedLoadWorkflows.mockClear();

            await wrapper.find(SELECTORS.BULK_UNSHARE_BUTTON).trigger("click");
            await flushPromises();

            expect(confirm).toHaveBeenCalledTimes(1);
            expect(unshared).toEqual(["shared-1", "shared-2"]);
            expect(mockedLoadWorkflows).toHaveBeenCalledTimes(1);
            expect(raisedToasts()).toEqual([
                { variant: "success", message: "Removed 2 workflows from your shared workflows." },
            ]);
        });

        it("keeps every share when removal is not confirmed", async () => {
            const workflows = serveSharedWorkflows();
            const unshared = interceptUnshare();
            confirm.mockResolvedValue(false);
            const wrapper = await mountWorkflowListForUser("shared_with_me");
            await selectCards(wrapper, workflows);

            await wrapper.find(SELECTORS.BULK_UNSHARE_BUTTON).trigger("click");
            await flushPromises();

            expect(confirm).toHaveBeenCalledTimes(1);
            expect(unshared).toEqual([]);
            expect(raisedToasts()).toEqual([]);
        });

        it("reports the workflows whose share could not be removed and keeps them selected", async () => {
            const workflows = serveSharedWorkflows();
            const unshared = interceptUnshare("shared-2");
            confirm.mockResolvedValue(true);
            const wrapper = await mountWorkflowListForUser("shared_with_me");
            await selectCards(wrapper, workflows);

            await wrapper.find(SELECTORS.BULK_UNSHARE_BUTTON).trigger("click");
            await flushPromises();

            expect(unshared).toEqual(["shared-1", "shared-2"]);
            expect(raisedToasts()).toEqual([
                { variant: "success", message: "Removed 1 workflow from your shared workflows." },
                { variant: "error", message: "Failed to remove 1 shared workflow: 'Shared 2' (Workflow not found)" },
            ]);
            expect(wrapper.find(SELECTORS.BULK_UNSHARE_BUTTON).text()).toContain("Remove from Shared (1)");
        });

        it("does nothing on the Delete key in the shared with me view", async () => {
            const [workflow] = serveSharedWorkflows();
            const unshared = interceptUnshare();
            confirm.mockResolvedValue(true);
            const wrapper = await mountWorkflowListForUser("shared_with_me");

            wrapper.findComponent(WorkflowCardList).vm.$emit("on-key-down", workflow, deleteKeyEvent());
            await flushPromises();

            expect(confirm).not.toHaveBeenCalled();
            expect(unshared).toEqual([]);
        });
    });

    it("keeps the newest list when an older load finishes last", async () => {
        const oldWorkflows = ownWorkflows(2, {}, "old");
        const newWorkflows = ownWorkflows(3, { deleted: true }, "new");
        const firstLoad = deferred<WorkflowListPage>();
        mockedLoadWorkflows
            .mockReturnValueOnce(firstLoad.promise)
            .mockResolvedValueOnce({ data: newWorkflows, totalMatches: 3 });
        const wrapper = await mountWorkflowListForUser();

        await wrapper.find(SELECTORS.SHOW_DELETED_BUTTON).trigger("click");
        await flushPromises();
        expect(wrapper.findAll(SELECTORS.WORKFLOW_CARD)).toHaveLength(3);

        firstLoad.resolve({ data: oldWorkflows, totalMatches: 2 });
        await flushPromises();

        expect(mockedLoadWorkflows).toHaveBeenCalledTimes(2);
        expect(wrapper.findAll(SELECTORS.WORKFLOW_CARD)).toHaveLength(3);
    });

    it("ignores an older load that fails while a newer one is still running", async () => {
        const newWorkflows = ownWorkflows(3, { deleted: true });
        const firstLoad = deferred<WorkflowListPage>();
        const secondLoad = deferred<WorkflowListPage>();
        mockedLoadWorkflows.mockReturnValueOnce(firstLoad.promise).mockReturnValueOnce(secondLoad.promise);
        const wrapper = await mountWorkflowListForUser();

        await wrapper.find(SELECTORS.SHOW_DELETED_BUTTON).trigger("click");
        await flushPromises();
        expect(mockedLoadWorkflows).toHaveBeenCalledTimes(2);

        firstLoad.reject(new Error("load failed"));
        await flushPromises();
        expect(raisedToasts()).toEqual([]);
        // The newer load is still running, so the list keeps showing that it is loading.
        expect(wrapper.findComponent(LoadingSpan).exists()).toBe(true);

        secondLoad.resolve({ data: newWorkflows, totalMatches: 3 });
        await flushPromises();
        expect(wrapper.findComponent(LoadingSpan).exists()).toBe(false);
        expect(wrapper.findAll(SELECTORS.WORKFLOW_CARD)).toHaveLength(3);
        expect(raisedToasts()).toEqual([]);
    });
});

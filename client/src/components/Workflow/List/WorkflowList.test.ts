import { createTestingPinia, type TestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getFakeWorkflowSummary } from "@tests/test-data/workflows";
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
import { useUserStore } from "@/stores/userStore";

import WorkflowList from "./WorkflowList.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const { server, http } = useServerMock();

vi.mock("@/api/workflows", () => ({
    loadWorkflows: vi.fn(),
}));

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
};

/** Serves the given workflows as the list's only page. */
function serveWorkflowList(workflows: WorkflowSummary[]) {
    mockedLoadWorkflows.mockResolvedValue({ data: workflows, totalMatches: workflows.length });
    return workflows;
}

/** Workflows owned by the fake user, served as the list's only page. */
function serveWorkflows(count: number, overrides: Partial<WorkflowSummary> = {}) {
    return serveWorkflowList(
        Array.from({ length: count }, (_, i) =>
            getFakeWorkflowSummary({ id: `workflow-${i}`, name: `Workflow ${i}`, owner: FAKE_USERNAME, ...overrides }),
        ),
    );
}

/** Mounts the list before any user has loaded; the "my" list waits for one. */
function mountWorkflowList(pinia: TestingPinia = createTestingPinia({ createSpy: vi.fn, stubActions: false })) {
    setActivePinia(pinia);
    const wrapper = mount(WorkflowList, { global: withPlugins(localVue, pinia, router) });
    return { wrapper, userStore: useUserStore() };
}

async function mountWorkflowListForUser() {
    const { wrapper, userStore } = mountWorkflowList();
    userStore.currentUser = FAKE_USER;
    await flushPromises();
    return wrapper;
}

function filterText(wrapper: VueWrapper) {
    return wrapper.find<HTMLInputElement>(SELECTORS.FILTER_INPUT).element.value;
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
        const { wrapper, userStore } = mountWorkflowList(createTestingPinia({ createSpy: vi.fn }));
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
});

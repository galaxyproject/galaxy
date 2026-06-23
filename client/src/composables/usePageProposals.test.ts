import { createTestingPinia } from "@pinia/testing";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { djb2Hash } from "@/components/PageEditor/sectionDiffUtils";
import type { ActiveContext } from "@/composables/useActiveContext";
import { usePageEditorStore } from "@/stores/pageEditorStore";

import { usePageProposals } from "./usePageProposals";

// Mock useUserLocalStorage so localStorage isn't touched in tests.
const mockPersistedDismissed = ref<Record<string, string[]>>({});
vi.mock("@/composables/userLocalStorage", () => ({
    useUserLocalStorage: () => mockPersistedDismissed,
}));

const PAGE_ID = "page-abc";
const PAGE_CONTENT = "# Intro\nSome intro text\n# Methods\nSome methods text";

const PAGE_CONTENT_HASH = djb2Hash(PAGE_CONTENT);

function makeNotebookContext(pageId = PAGE_ID): ActiveContext {
    return { contextType: "notebook", pageId, historyId: "hist-1" };
}

function makeMsg(overrides: Record<string, unknown> = {}) {
    return {
        id: "msg-1",
        role: "assistant" as const,
        content: "Here is my suggestion.",
        timestamp: new Date(),
        feedback: null,
        ...overrides,
    };
}

function makeProposalMsg(
    mode: "full_replacement" | "section_patch",
    content: string,
    extras: Record<string, unknown> = {},
) {
    return makeMsg({
        agentResponse: {
            agent_type: "page_assistant",
            confidence: "high",
            suggestions: [],
            metadata: {
                edit_mode: mode,
                content,
                original_content_hash: PAGE_CONTENT_HASH,
                ...extras,
            },
        },
    });
}

describe("usePageProposals", () => {
    beforeEach(() => {
        setActivePinia(createTestingPinia({ createSpy: vi.fn }));
        mockPersistedDismissed.value = {};
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    function setup(initialContext: ActiveContext | null = makeNotebookContext()) {
        const activeContext = ref<ActiveContext | null>(initialContext);
        const store = usePageEditorStore();
        store.currentContent = PAGE_CONTENT;
        vi.mocked(store.savePage).mockResolvedValue(undefined);
        const composable = usePageProposals(activeContext);
        return { activeContext, store, ...composable };
    }

    describe("pageContent", () => {
        it("returns store content when in notebook context", () => {
            const { pageContent } = setup();
            expect(pageContent.value).toBe(PAGE_CONTENT);
        });

        it("returns empty string when context is null", () => {
            const { pageContent } = setup(null);
            expect(pageContent.value).toBe("");
        });

        it("returns empty string for non-notebook context types", () => {
            const { pageContent } = setup({ contextType: "tool", toolId: "bwa" });
            expect(pageContent.value).toBe("");
        });
    });

    describe("loadForPage / clear", () => {
        it("loads dismissed proposals from localStorage for a page", () => {
            mockPersistedDismissed.value[PAGE_ID] = ["msg-1", "msg-2"];
            const { loadForPage, dismissedProposals } = setup();

            loadForPage(PAGE_ID);

            expect(dismissedProposals.value.has("msg-1")).toBe(true);
            expect(dismissedProposals.value.has("msg-2")).toBe(true);
        });

        it("clear resets the in-memory set", () => {
            mockPersistedDismissed.value[PAGE_ID] = ["msg-1"];
            const { loadForPage, clear, dismissedProposals } = setup();
            loadForPage(PAGE_ID);
            expect(dismissedProposals.value.size).toBe(1);

            clear();
            expect(dismissedProposals.value.size).toBe(0);
        });
    });

    describe("getEditProposal", () => {
        it("returns null for messages without agentResponse", () => {
            const { getEditProposal } = setup();
            expect(getEditProposal(makeMsg())).toBeNull();
        });

        it("returns null when edit_mode is absent", () => {
            const { getEditProposal } = setup();
            const msg = makeMsg({ agentResponse: { metadata: {} } });
            expect(getEditProposal(msg)).toBeNull();
        });

        it("returns full_replacement proposal", () => {
            const { getEditProposal } = setup();
            const msg = makeProposalMsg("full_replacement", "new content");
            const proposal = getEditProposal(msg);
            expect(proposal?.mode).toBe("full_replacement");
            expect(proposal?.content).toBe("new content");
        });

        it("returns section_patch proposal with target heading", () => {
            const { getEditProposal } = setup();
            const msg = makeProposalMsg("section_patch", "", {
                target_section_heading: "Methods",
                new_section_content: "## Methods\nNew methods text",
            });
            const proposal = getEditProposal(msg);
            expect(proposal?.mode).toBe("section_patch");
            expect(proposal?.target_section_heading).toBe("Methods");
        });
    });

    describe("isProposalStale", () => {
        it("returns false when no original_content_hash in metadata", () => {
            const { isProposalStale } = setup();
            const msg = makeMsg({
                agentResponse: { metadata: { edit_mode: "full_replacement", content: "x" } },
            });
            expect(isProposalStale(msg)).toBe(false);
        });

        it("returns false when hash matches current content", () => {
            const { isProposalStale } = setup();
            const msg = makeProposalMsg("full_replacement", "x");
            expect(isProposalStale(msg)).toBe(false);
        });

        it("returns true when hash does not match current content", () => {
            const { store, isProposalStale } = setup();
            store.currentContent = "# Changed content";
            const msg = makeProposalMsg("full_replacement", "x"); // hash is for original PAGE_CONTENT
            expect(isProposalStale(msg)).toBe(true);
        });
    });

    describe("isProposalVisible", () => {
        it("returns false when not in notebook context", () => {
            const { isProposalVisible } = setup(null);
            const msg = makeProposalMsg("full_replacement", "new");
            expect(isProposalVisible(msg)).toBe(false);
        });

        it("returns false when message is dismissed", () => {
            const { isProposalVisible, dismissProposal } = setup();
            const msg = makeProposalMsg("full_replacement", "new");
            dismissProposal(msg);
            expect(isProposalVisible(msg)).toBe(false);
        });

        it("returns false when message has no proposal", () => {
            const { isProposalVisible } = setup();
            expect(isProposalVisible(makeMsg())).toBe(false);
        });

        it("returns false for full_replacement when content already matches page", () => {
            const { isProposalVisible } = setup();
            const msg = makeProposalMsg("full_replacement", PAGE_CONTENT);
            expect(isProposalVisible(msg)).toBe(false);
        });

        it("returns true for a fresh full_replacement proposal", () => {
            const { isProposalVisible } = setup();
            const msg = makeProposalMsg("full_replacement", "brand new content");
            expect(isProposalVisible(msg)).toBe(true);
        });

        it("returns true for a section_patch proposal", () => {
            const { isProposalVisible } = setup();
            const msg = makeProposalMsg("section_patch", "", {
                target_section_heading: "Methods",
                new_section_content: "## Methods\nUpdated",
            });
            expect(isProposalVisible(msg)).toBe(true);
        });
    });

    describe("buildProposedContent", () => {
        it("returns pageContent when no proposal", () => {
            const { buildProposedContent } = setup();
            expect(buildProposedContent(makeMsg())).toBe(PAGE_CONTENT);
        });

        it("returns proposal content directly for full_replacement", () => {
            const { buildProposedContent } = setup();
            const msg = makeProposalMsg("full_replacement", "completely new doc");
            expect(buildProposedContent(msg)).toBe("completely new doc");
        });

        it("applies section patch to produce full document", () => {
            const { buildProposedContent } = setup();
            const msg = makeProposalMsg("section_patch", "", {
                target_section_heading: "Methods",
                new_section_content: "# Methods\nReplaced methods",
            });
            const result = buildProposedContent(msg);
            expect(result).toContain("Replaced methods");
            expect(result).toContain("Intro");
        });
    });

    describe("dismissProposal", () => {
        it("adds message ID to dismissed set", () => {
            const { dismissedProposals, dismissProposal } = setup();
            const msg = makeProposalMsg("full_replacement", "x");
            dismissProposal(msg);
            expect(dismissedProposals.value.has(msg.id)).toBe(true);
        });

        it("persists dismissed ID to localStorage", () => {
            const { dismissProposal } = setup();
            const msg = makeProposalMsg("full_replacement", "x");
            dismissProposal(msg);
            expect(mockPersistedDismissed.value[PAGE_ID]).toContain(msg.id);
        });

        it("does not persist to localStorage when not in notebook context", () => {
            const { activeContext, dismissProposal } = setup();
            activeContext.value = null;
            dismissProposal(makeProposalMsg("full_replacement", "x"));
            expect(mockPersistedDismissed.value[PAGE_ID]).toBeUndefined();
        });

        it("persisted dismissal survives a loadForPage reload", () => {
            const { dismissProposal, loadForPage, dismissedProposals } = setup();
            const msg = makeProposalMsg("full_replacement", "x");
            dismissProposal(msg);
            dismissedProposals.value = new Set();
            loadForPage(PAGE_ID);
            expect(dismissedProposals.value.has(msg.id)).toBe(true);
        });
    });

    describe("applyFullReplacement", () => {
        it("updates store content and saves", async () => {
            const { store, applyFullReplacement } = setup();
            const msg = makeProposalMsg("full_replacement", "new page content");
            await applyFullReplacement(msg);
            await flushPromises();

            expect(store.updateContent).toHaveBeenCalledWith("new page content");
            expect(store.savePage).toHaveBeenCalledWith("agent");
        });

        it("marks message as dismissed after applying", async () => {
            const { dismissedProposals, applyFullReplacement } = setup();
            const msg = makeProposalMsg("full_replacement", "new page content");
            await applyFullReplacement(msg);
            expect(dismissedProposals.value.has(msg.id)).toBe(true);
        });

        it("does nothing when message has no proposal", async () => {
            const { store, applyFullReplacement } = setup();
            await applyFullReplacement(makeMsg());
            expect(store.updateContent).not.toHaveBeenCalled();
        });
    });

    describe("applySectionPatched", () => {
        it("updates store with patched content and saves", async () => {
            const { store, applySectionPatched } = setup();
            const msg = makeProposalMsg("section_patch", "");
            await applySectionPatched("# Patched doc", msg);
            await flushPromises();

            expect(store.updateContent).toHaveBeenCalledWith("# Patched doc");
            expect(store.savePage).toHaveBeenCalledWith("agent");
        });

        it("marks message as dismissed after applying", async () => {
            const { dismissedProposals, applySectionPatched } = setup();
            const msg = makeProposalMsg("section_patch", "", {
                target_section_heading: "Methods",
                new_section_content: "# Methods\nUpdated",
            });
            await applySectionPatched("# Patched doc", msg);
            expect(dismissedProposals.value.has(msg.id)).toBe(true);
        });
    });
});

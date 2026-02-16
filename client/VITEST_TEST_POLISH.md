# ChatGXY Vitest Test Polish Items

Low-priority issues from vitest review of `src/components/ChatGXY/` test files.
All 12 mutation tests killed — tests are catching real behavior.

## agentTypes.test.ts

1. **`agentTypes` count assertion is a magic number** (line 16): `expect(agentTypes).toHaveLength(6)` must be updated every time an agent is added. Consider replacing with a structural check (e.g., verify each value maps to an icon) or dropping the count entirely — the `has expected agent values` test already locks the set.

2. **`agentIconMap` block overlaps with `getAgentIcon` tests** (lines 33-42): Both test the same mapping. `getAgentIcon` is the public API consumers use; `agentIconMap` is the underlying data. Consider consolidating since `getAgentIcon` coverage is sufficient and testing the map directly is implementation-coupled.

3. **`formatModelName` trailing-slash test documents surprising behavior** (line 101-104): `formatModelName("openai/")` returns `"openai/"` because `parts.pop()` yields `""` which triggers the `|| model` fallback. This may be intentional or a bug in the source — worth a comment or source fix.

## ChatMessageCell.test.ts

4. **Action suggestion tests rely on ActionCard's real `.action-card` CSS class** (lines 189-206): `stubs: { ActionCard: true }` doesn't actually stub `<script setup>` components in vue-test-utils v1, so the real ActionCard renders. Assertions use `wrapper.find(".action-card")` which is ActionCard's own class, coupling this test to ActionCard's template. If ActionCard changes its root class, this test fails for the wrong reason. Consider `wrapper.findComponent(ActionCard).exists()` if it works with the real component.

5. **Unused `AgentResponse` type import** (line 4): `AgentResponse` is imported but never directly referenced — it's only used implicitly through `ChatMessage.agentResponse`. Harmless since it's a `type` import, but worth removing for clarity.

## chatUtils.test.ts

6. **No `afterEach` mock cleanup** (missing): `vi.fn()` is used for the scrollTo mock but there's no `afterEach(() => vi.restoreAllMocks())`. Not currently a problem since each test creates a fresh mock, but violates best practices and could bite if tests grow.

7. **Uniqueness test uses arbitrary count** (line 24): `100` IDs is fine for documenting intent but Math.random collisions with 9 chars of base36 are astronomically unlikely. Not a real issue — just noting it's a documentation test, not a probabilistic guarantee.

## ChatInput.test.ts

8. **Default placeholder test uses partial match** (line 31): `toContain("Ask about tools")` could match a different substring if the placeholder text changes in unexpected ways. Consider `toBe()` with the full default string for an exact assertion.

import { ref } from "vue";

import { GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

/**
 * Tutor ("learning") mode for the Galaxy AI panel.
 *
 * When enabled, chat exchanges are routed to the `teaching_assistant` agent for
 * Socratic, guided answers instead of the default router. The learning state
 * (mode, scaffolding level, inferred expertise) is persisted per-user on the
 * backend via the `/api/chat/tutor/*` endpoints, so it survives reloads.
 */
export function useTutorMode() {
    const tutorModeEnabled = ref(false);
    const scaffoldingLevel = ref<number | null>(null);
    const expertiseLevel = ref<string | null>(null);
    const loading = ref(false);

    function applyState(state: Record<string, unknown> | null | undefined) {
        if (!state) {
            return;
        }
        tutorModeEnabled.value = Boolean(state.tutor_mode_enabled);
        scaffoldingLevel.value = typeof state.scaffolding_level === "number" ? state.scaffolding_level : null;
        expertiseLevel.value = typeof state.expertise_level === "string" ? state.expertise_level : null;
    }

    async function fetchTutorState() {
        loading.value = true;
        try {
            const { data, error } = await GalaxyApi().GET("/api/chat/tutor/state");
            if (error) {
                rethrowSimple(error);
            }
            applyState(data as Record<string, unknown>);
        } finally {
            loading.value = false;
        }
    }

    async function setTutorMode(enabled: boolean) {
        loading.value = true;
        try {
            const { data, error } = await GalaxyApi().POST("/api/chat/tutor/mode", { body: enabled });
            if (error) {
                rethrowSimple(error);
            }
            const result = data as { enabled?: boolean; state?: Record<string, unknown> };
            tutorModeEnabled.value = Boolean(result?.enabled);
            applyState(result?.state);
        } finally {
            loading.value = false;
        }
    }

    function toggleTutorMode() {
        return setTutorMode(!tutorModeEnabled.value);
    }

    return {
        tutorModeEnabled,
        scaffoldingLevel,
        expertiseLevel,
        loading,
        fetchTutorState,
        setTutorMode,
        toggleTutorMode,
    };
}

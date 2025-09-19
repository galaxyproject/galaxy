/**
 * Read-only class for dataset states in a collection.
 * Similar to JobStateSummary but for dataset states.
 */
import { ERROR_DATASET_STATES, NON_TERMINAL_DATASET_STATES } from "@/api/datasets";

interface HDCAWithDatasetStates {
    elements_states?: Record<string, number>;
    elements_deleted?: number;
    populated_state?: string | null;
}

export class DatasetStateSummary {
    elements_states: Record<string, number>;
    elements_deleted: number;
    populated_state: string | null;

    constructor(hdca: HDCAWithDatasetStates = {}) {
        this.elements_states = hdca.elements_states || {};
        this.elements_deleted = hdca.elements_deleted || 0;
        this.populated_state = hdca.populated_state || null;
    }

    get(state: string): number {
        return this.elements_states[state] || 0;
    }

    get datasetCount(): number {
        return Object.values(this.elements_states).reduce((sum, count) => sum + count, 0);
    }

    private getCount(states: string[]): number {
        return states.reduce((sum, state) => sum + this.get(state), 0);
    }

    get okCount(): number {
        return this.getCount(["ok", "empty", "deferred"]);
    }

    get errorCount(): number {
        return this.getCount(["error", "failed_metadata"]);
    }

    get runningCount(): number {
        return this.getCount(["running", "setting_metadata"]);
    }

    get waitingCount(): number {
        return this.getCount(["queued", "new", "upload", "paused"]);
    }

    get deferredCount(): number {
        return this.getCount(["deferred", "discarded"]);
    }

    get isTerminal(): boolean {
        return !NON_TERMINAL_DATASET_STATES.some((state) => this.get(state) > 0);
    }

    get state(): string {
        if (this.datasetCount === 0) {
            return this.populated_state || "new";
        }

        if (this.errorCount > 0) {
            return "error";
        }

        if (this.runningCount > 0) {
            return "running";
        }

        if (this.waitingCount > 0) {
            return "queued";
        }

        if (this.deferredCount > 0) {
            return "deferred";
        }

        if (this.isTerminal) {
            return "ok";
        }

        return "new";
    }
}

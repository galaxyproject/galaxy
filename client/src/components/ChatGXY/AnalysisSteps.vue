<script setup lang="ts">
import type { AnalysisStep } from "./types";

const props = defineProps<{
    steps: AnalysisStep[];
}>();
</script>

<template>
    <div class="analysis-steps card">
        <div
            v-for="(step, idx) in props.steps"
            :key="idx"
            class="analysis-step"
            :class="[step.type, step.status && step.status !== 'pending' ? step.status : '']">
            <div class="analysis-step-header">
                <span class="step-label">
                    {{
                        step.type === "thought"
                            ? "Plan"
                            : step.type === "action"
                              ? "Action"
                              : step.type === "observation"
                                ? "Observation"
                                : "Conclusion"
                    }}
                </span>
                <span
                    v-if="step.type === 'action' && step.status && step.status !== 'pending'"
                    class="step-status"
                    :class="step.status">
                    {{ step.status }}
                </span>
                <span
                    v-else-if="step.type === 'observation' && step.success !== undefined"
                    class="step-status"
                    :class="step.success ? 'completed' : 'error'">
                    {{ step.success ? "success" : "error" }}
                </span>
            </div>

            <div class="analysis-step-body">
                <pre v-if="step.type === 'action'">{{ step.content }}</pre>
                <div v-else-if="step.type === 'observation'">
                    <div v-if="step.stdout">
                        <small class="text-muted">stdout</small>
                        <pre>{{ step.stdout }}</pre>
                    </div>
                    <div v-if="step.stderr">
                        <small class="text-muted">stderr</small>
                        <pre class="text-danger">{{ step.stderr }}</pre>
                    </div>
                    <div v-if="!step.stdout && !step.stderr">No textual output.</div>
                </div>
                <div v-else>{{ step.content }}</div>
                <div v-if="step.type === 'action' && step.requirements?.length" class="step-requirements">
                    <small class="text-muted"> requirements: {{ step.requirements.join(", ") }} </small>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.analysis-steps {
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 0.75rem;
    background: white;

    .analysis-step + .analysis-step {
        margin-top: 0.75rem;
    }

    .analysis-step-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-weight: 600;
        font-size: 0.9rem;

        .step-label {
            text-transform: capitalize;
        }
    }

    .analysis-step-header .step-status {
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        padding: 0.1rem 0.4rem;
        border-radius: 9999px;
        margin-left: 0.5rem;
    }

    .analysis-step.running .step-status {
        background: #fff3cd;
        color: #856404;
    }

    .analysis-step.completed .step-status {
        background: #d4edda;
        color: #155724;
    }

    .analysis-step.error .step-status {
        background: #f8d7da;
        color: #721c24;
    }

    .analysis-step-body {
        margin-top: 0.5rem;
        font-size: 0.9rem;

        pre {
            background: #f1f3f5;
            color: #212529;
            padding: 0.5rem;
            border-radius: 4px;
            white-space: pre-wrap;
            border: 1px solid #d1d5db;
        }

        .text-danger {
            color: #dc3545 !important;
        }

        .step-requirements {
            margin-top: 0.35rem;
            font-size: 0.75rem;
        }
    }
}
</style>

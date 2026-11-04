<script setup lang="ts">
import { computed } from "vue";

import type { WorkflowInputSection } from "@/components/Workflow/Run/inputSections";
import type { Step } from "@/stores/workflowStepStore";

import FormElement from "@/components/Form/FormElement.vue";

const NO_SECTION = "__no_section__";
const NEW_SECTION = "__new_section__";

const props = defineProps<{
    step: Step;
    inputSections: WorkflowInputSection[];
}>();

const emit = defineEmits<{
    (e: "onUpdateStep", id: number, value: Partial<Step>): void;
    (e: "onUpdateInputSections", sections: WorkflowInputSection[]): void;
}>();

const currentSection = computed(() =>
    props.step.section ? props.inputSections.find((section) => section.name === props.step.section) : undefined,
);

const sectionOptions = computed(() => {
    const options = [{ value: NO_SECTION, label: "None" }];
    for (const section of props.inputSections) {
        options.push({ value: section.name, label: section.label || section.name });
    }
    if (props.step.section && !currentSection.value) {
        options.push({ value: props.step.section, label: props.step.section });
    }
    options.push({ value: NEW_SECTION, label: "New section..." });
    return options;
});

function newSection(): WorkflowInputSection {
    const names = new Set(props.inputSections.map((section) => section.name));
    let index = props.inputSections.length + 1;
    while (names.has(`section_${index}`)) {
        index++;
    }
    return { name: `section_${index}`, label: `Section ${index}`, expanded: false };
}

function onSelectSection(value: string) {
    if (value === NEW_SECTION) {
        const section = newSection();
        emit("onUpdateInputSections", [...props.inputSections, section]);
        emit("onUpdateStep", props.step.id, { section: section.name });
    } else if (value === NO_SECTION) {
        emit("onUpdateStep", props.step.id, { section: undefined });
    } else if (value !== props.step.section) {
        emit("onUpdateStep", props.step.id, { section: value });
    }
}

function updateCurrentSection(changes: Partial<WorkflowInputSection>) {
    const name = props.step.section;
    if (!name) {
        return;
    }
    if (currentSection.value) {
        emit(
            "onUpdateInputSections",
            props.inputSections.map((section) => (section.name === name ? { ...section, ...changes } : section)),
        );
    } else {
        emit("onUpdateInputSections", [...props.inputSections, { name, expanded: false, ...changes }]);
    }
}
</script>

<template>
    <div class="form-input-section">
        <FormElement
            id="__input_section"
            :value="step.section || NO_SECTION"
            :attributes="{ data: sectionOptions }"
            :optional="false"
            type="select"
            title="Present under section"
            help="Group this input with others under a collapsible section of the workflow run form. Sections appear where their first input appears."
            @input="onSelectSection" />
        <template v-if="step.section">
            <FormElement
                id="__input_section_label"
                :value="currentSection?.label || step.section"
                type="text"
                title="Section label"
                help="Heading of the section in the run form, shared by all of its inputs."
                @input="(label: string) => updateCurrentSection({ label })" />
            <FormElement
                id="__input_section_expanded"
                :value="Boolean(currentSection?.expanded)"
                type="boolean"
                title="Expand section by default"
                help="Collapsed sections still open in the run form while one of their required inputs has no value."
                @input="(expanded: boolean) => updateCurrentSection({ expanded })" />
        </template>
    </div>
</template>

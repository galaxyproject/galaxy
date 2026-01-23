<script setup lang="ts">
import {
    faCheck,
    faExclamationTriangle,
    faMagic,
    faPencilAlt,
    faSave,
    faSearch,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import { dataAttributes, type LintState } from "./modules/linting";

import GButton from "@/components/BaseComponents/GButton.vue";
import GLink from "@/components/BaseComponents/GLink.vue";
import GCard from "@/components/Common/GCard.vue";

interface Props {
    successMessage: string;
    warningMessage: string;
    okay?: boolean;
    attributeLink?: string;
    warningItems?: LintState[] | null;
    requiresSave?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    okay: true,
    attributeLink: "Edit Workflow Attributes",
    warningItems: null,
    requiresSave: false,
});

const emit = defineEmits<{
    (e: "onClick", item: LintState): void;
    (e: "onMouseOver", item: LintState): void;
    (e: "onMouseLeave", item: LintState): void;
    (e: "onClickAttribute"): void;
    (e: "onSaveRequested"): void;
}>();

const hasWarningItems = computed(() => props.warningItems && props.warningItems.length > 0);
const isOkay = computed(() => props.okay && !hasWarningItems.value);
</script>

<template>
    <GCard :data-lint-status="isOkay ? 'ok' : 'warning'">
        <div v-if="isOkay">
            <FontAwesomeIcon :icon="faCheck" class="text-success" />
            <span v-localize>{{ props.successMessage }}</span>
        </div>
        <div v-else>
            <FontAwesomeIcon :icon="faExclamationTriangle" class="text-warning" />
            <span v-localize>{{ props.warningMessage }}</span>

            <div v-if="hasWarningItems" class="mt-2">
                <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
                <div
                    v-for="(item, idx) in props.warningItems"
                    :key="idx"
                    class="ml-2"
                    @focusin="emit('onMouseOver', item)"
                    @mouseover="emit('onMouseOver', item)"
                    @focusout="emit('onMouseLeave', item)"
                    @mouseleave="emit('onMouseLeave', item)">
                    <GLink
                        class="scrolls"
                        thin
                        :disabled="props.requiresSave"
                        disabled-title="Fix disabled. Save workflow to enable this fix."
                        :data-item-index="idx"
                        v-bind="dataAttributes(item)"
                        @click="emit('onClick', item)">
                        <FontAwesomeIcon v-if="item.autofix" :icon="faMagic" class="mr-1" />
                        <FontAwesomeIcon v-else :icon="faSearch" class="mr-1" />
                        <strong>Step {{ item.stepId + 1 }}</strong>
                        {{ item.stepLabel }}: {{ item.warningLabel }}
                    </GLink>
                </div>
            </div>
            <p v-else class="mt-2 ml-1 my-0">
                <GLink thin @click="emit('onClickAttribute')">
                    <FontAwesomeIcon :icon="faPencilAlt" class="mr-1" />{{ props.attributeLink }}
                </GLink>
            </p>

            <GButton
                v-if="props.requiresSave"
                color="blue"
                class="d-flex w-100 justify-content-center my-2"
                @click="emit('onSaveRequested')">
                <FontAwesomeIcon :icon="faSave" class="mr-1" />
                Enable Fixes by Saving
            </GButton>
        </div>
    </GCard>
</template>

<style scoped lang="scss">
.g-link {
    text-align: initial;
}
</style>

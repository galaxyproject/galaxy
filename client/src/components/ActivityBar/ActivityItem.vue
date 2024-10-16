<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import type { Placement } from "@popperjs/core";
import { useRouter } from "vue-router/composables";

import type { ActivityVariant } from "@/stores/activityStore";
import localize from "@/utils/localization";

import TextShort from "@/components/Common/TextShort.vue";
import Popper from "@/components/Popper/Popper.vue";

const router = useRouter();

interface Option {
    name: string;
    value: string;
}

export interface Props {
    id: string;
    title?: string;
    icon?: string | object;
    indicator?: number;
    isActive?: boolean;
    tooltip?: string;
    tooltipPlacement?: Placement;
    progressPercentage?: number;
    progressStatus?: string;
    options?: Option[];
    to?: string;
    variant?: ActivityVariant;
}

const props = withDefaults(defineProps<Props>(), {
    title: undefined,
    icon: "question",
    indicator: 0,
    isActive: false,
    options: undefined,
    progressPercentage: 0,
    progressStatus: undefined,
    to: undefined,
    tooltip: undefined,
    tooltipPlacement: "right",
    variant: "primary",
});

const emit = defineEmits<{
    (e: "click"): void;
}>();

function onClick(evt: MouseEvent): void {
    emit("click");
    if (props.to) {
        router.push(props.to);
    }
}
</script>

<template>
    <Popper reference-is="span" popper-is="span" :placement="tooltipPlacement">
        <template v-slot:reference>
            <b-nav-item
                class="activity-item position-relative my-1 p-2"
                :class="{ 'nav-item-active': isActive }"
                :link-classes="`variant-${props.variant}`"
                :aria-label="localize(title)"
                @click="onClick">
                <span v-if="progressStatus" class="progress">
                    <div
                        class="progress-bar notransition"
                        :class="{
                            'bg-danger': progressStatus === 'danger',
                            'bg-success': progressStatus === 'success',
                        }"
                        :style="{
                            width: `${Math.round(progressPercentage)}%`,
                        }" />
                </span>
                <div class="nav-icon">
                    <span v-if="indicator > 0" class="nav-indicator" data-description="activity indicator">
                        {{ Math.min(indicator, 99) }}
                    </span>
                    <FontAwesomeIcon :icon="icon" />
                </div>
                <TextShort v-if="title" :text="title" class="nav-title" />
            </b-nav-item>
        </template>
        <div class="text-center px-2 py-1">
            <small v-if="tooltip">{{ localize(tooltip) }}</small>
            <small v-else>No tooltip available for this item</small>
            <div v-if="options" class="nav-options p-1">
                <router-link v-for="(option, index) in options" :key="index" :to="option.value">
                    <b-button size="sm" variant="outline-primary" class="w-100 my-1 text-break text-light">
                        {{ option.name }}
                    </b-button>
                </router-link>
            </div>
        </div>
    </Popper>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.activity-item {
    display: flex;
    flex-direction: column;

    &:deep(.variant-danger) {
        color: $brand-danger;
    }

    &:deep(.variant-disabled) {
        color: $text-light;
    }
}

.nav-icon {
    display: flex;
    justify-content: center;
    cursor: pointer;
    font-size: 1rem;
}

.nav-indicator {
    align-items: center;
    background: $brand-danger;
    border-radius: 50%;
    color: $brand-light;
    display: flex;
    font-size: 0.7rem;
    justify-content: center;
    left: 2.2rem;
    height: 1.2rem;
    position: absolute;
    top: -0.3rem;
    width: 1.2rem;
}

.nav-item-active {
    border-radius: $border-radius-extralarge;
    background: $gray-300;
}

.nav-link {
    padding: 0;
}

.nav-options {
    overflow-x: hidden;
    overflow-y: auto;
}

.nav-title {
    display: flex;
    justify-content: center;
    width: 4rem;
    margin-top: 0.5rem;
    font-size: 0.7rem;
}

.progress {
    background: transparent;
    border-radius: $border-radius-extralarge;
    position: absolute;
    width: 100%;
    height: 100%;
    left: 0;
    top: 0;
}

.notransition {
    -webkit-transition: none;
    -moz-transition: none;
    -ms-transition: none;
    -o-transition: none;
    transition: none;
}
</style>

<template>
    <span>
        <span v-if="!referenceEl" ref="reference">
            <slot name="reference" />
        </span>
        <div v-show="!disabled && visible" ref="popper" class="popper-element" :class="`popper-element-${mode}`">
            <div v-if="arrow" class="popper-arrow" data-popper-arrow />
            <div v-if="title" class="popper-header px-2 py-1 rounded-top d-flex justify-content-between">
                <span class="px-1">{{ title }}</span>
                <span class="popper-close align-items-center cursor-pointer" @click="visible = false">
                    <FontAwesomeIcon icon="fa-times-circle" />
                </span>
            </div>
            <slot />
        </div>
    </span>
</template>

<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimesCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { type Placement } from "@popperjs/core";
import type { PropType } from "vue";
import { ref } from "vue";

import { type Trigger, usePopper } from "./usePopper";

library.add(faTimesCircle);

const props = defineProps({
    arrow: { type: Boolean, default: true },
    disabled: { type: Boolean, default: false },
    mode: { type: String, default: "dark" },
    placement: String as PropType<Placement>,
    referenceEl: HTMLElement,
    title: String,
    trigger: String as PropType<Trigger>,
});

const reference = props.referenceEl ? ref(props.referenceEl) : ref();

const popper = ref();

const { visible } = usePopper(reference, popper, {
    placement: props.placement,
    trigger: props.trigger,
});

defineExpose({
    visible,
    reference,
    popper,
});
</script>

<style scoped lang="scss">
@import "theme/blue.scss";

@function popper-border($border-color) {
    @return 1px solid $border-color;
}

.popper-element {
    z-index: 9999;
    border-radius: $border-radius-large;
}

/** Available variants */
.popper-element-dark {
    background: $brand-dark;
    border: popper-border($brand-dark);
    color: $brand-light;
    max-width: 12rem;
    opacity: 0.95;
}

.popper-element-light {
    background: $white;
    border: popper-border($border-color);
    color: $brand-dark;
}

.popper-element-primary-title {
    background: $white;
    border: popper-border($border-color);
    color: $brand-dark;
    .popper-header {
        background: $brand-primary;
        color: $white;
    }
}

/** Triangle Arrow */
.popper-arrow {
    position: absolute;
    width: 0;
    height: 0;
    border-style: solid;
}

/** Arrow positioning based on placement */
.popper-element[data-popper-placement^="top"] > .popper-arrow {
    bottom: -14px;
    left: 50%;
    transform: translateX(-50%);
    border-width: 7px;
    border-color: $brand-dark transparent transparent transparent;
}

.popper-element[data-popper-placement^="bottom"] > .popper-arrow {
    top: -14px;
    left: 50%;
    transform: translateX(-50%);
    border-width: 7px;
    border-color: transparent transparent $brand-dark transparent;
}

.popper-element[data-popper-placement^="left"] > .popper-arrow {
    right: -14px;
    top: 50%;
    transform: translateY(-50%);
    border-width: 7px;
    border-color: transparent transparent transparent $brand-dark;
}

.popper-element[data-popper-placement^="right"] > .popper-arrow {
    left: -14px;
    top: 50%;
    transform: translateY(-50%);
    border-width: 7px;
    border-color: transparent $brand-dark transparent transparent;
}
</style>

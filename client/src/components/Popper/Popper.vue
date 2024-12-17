<template>
    <span>
        <span ref="reference">
            <slot name="reference" />
        </span>
        <div v-show="visible" ref="popper" class="popper-element mt-1" :class="`popper-element-${mode}`">
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
import type { PropType } from "vue";
import { ref, watch } from "vue";
import { type Placement } from "@popperjs/core";
import { usePopper, type Trigger } from "./usePopper";

library.add(faTimesCircle);

const props = defineProps({
    arrow: { type: Boolean, default: true },
    disabled: { type: Boolean, default: false },
    mode: { type: String, default: "dark" },
    placement: String as PropType<Placement>,
    title: String,
    trigger: String as PropType<Trigger>,
});

const reference = ref();
const popper = ref();

const { visible } = usePopper(reference, popper, {
    placement: props.placement,
    trigger: props.trigger,
});

watch(
    () => [visible.value, props.disabled],
    () => {
        if (props.disabled && visible.value) {
            visible.value = false;
        }
    },
    { flush: "sync" }
);

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
    .popper-arrow:before {
        background: $brand-dark;
        border: popper-border($brand-dark);
    }
}

.popper-element-light {
    background: $white;
    border: popper-border($border-color);
    color: $brand-dark;
    .popper-arrow:before {
        background: $white;
        border: popper-border($border-color);
    }
}

.popper-element-primary-title {
    background: $white;
    border: popper-border($border-color);
    color: $brand-dark;
    .popper-header {
        background: $brand-primary;
        color: $white;
    }
    .popper-arrow:before {
        background: $brand-primary;
        border: popper-border($border-color);
    }
}

/** Arrow positioning and border handling */
.popper-arrow,
.popper-arrow:before {
    height: 9px;
    width: 9px;
    position: absolute;
    content: "";
    transform: rotate(45deg);
}

.popper-element[data-popper-placement^="top"] {
    > .popper-arrow {
        bottom: 0px;
    }
    > .popper-arrow:before {
        bottom: -5px;
        border-top: none;
        border-left: none;
    }
}

.popper-element[data-popper-placement^="right"] {
    > .popper-arrow {
        left: 0px;
    }
    > .popper-arrow:before {
        left: -5px;
        border-top: none;
        border-right: none;
    }
}

.popper-element[data-popper-placement^="bottom"] {
    > .popper-arrow {
        top: 0px;
    }
    > .popper-arrow:before {
        top: -5px;
        border-bottom: none;
        border-right: none;
    }
}

.popper-element[data-popper-placement^="left"] {
    > .popper-arrow {
        right: 0px;
    }
    > .popper-arrow:before {
        right: -5px;
        border-bottom: none;
        border-left: none;
    }
}
</style>

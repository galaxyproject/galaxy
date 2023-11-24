<template>
    <div>
        <component :is="referenceIs" v-bind="referenceProps" ref="reference">
            <slot name="reference" />
        </component>
        <component
            :is="popperIs"
            v-show="visible"
            v-bind="popperProps"
            ref="popper"
            class="popper-element mt-1"
            :class="{ 'popper-element-dark': darkMode, 'popper-element-light': !darkMode }">
            <div v-if="darkMode" class="popper-arrow" data-popper-arrow />
            <slot />
        </component>
    </div>
</template>

<script lang="ts">
import { defineComponent, ref, toRef, watch } from "vue";
import type { UnwrapRef, PropType } from "vue";
import { usePopperjs } from "./usePopper";

export default defineComponent({
    components: {},

    props: {
        // hook options
        delayOnMouseout: Number,
        delayOnMouseover: Number,
        trigger: String as PropType<
            Exclude<UnwrapRef<Required<Parameters<typeof usePopperjs>>["2"]["trigger"]>, "manual">
        >,
        forceShow: Boolean,
        modifiers: Array as PropType<Required<Parameters<typeof usePopperjs>>["2"]["modifiers"]>,
        onFirstUpdate: Function as PropType<Required<Parameters<typeof usePopperjs>>["2"]["onFirstUpdate"]>,
        placement: String as PropType<Required<Parameters<typeof usePopperjs>>["2"]["placement"]>,
        strategy: String as PropType<Required<Parameters<typeof usePopperjs>>["2"]["strategy"]>,

        // component props
        popperIs: {
            default: "div",
            type: String,
        },
        popperProps: {
            type: Object,
        },
        referenceIs: {
            default: "div",
            type: String,
        },
        referenceProps: {
            type: Object,
        },
        disabled: {
            type: Boolean,
            default: false,
        },
        darkMode: {
            type: Boolean,
            default: true,
        },
    },

    emits: [
        "show",
        "hide",
        "before-enter",
        "enter",
        "after-enter",
        "enter-cancelled",
        "before-leave",
        "leave",
        "after-leave",
        "leave-cancelled",
    ],

    setup(props, { emit }) {
        const reference = ref();
        const popper = ref();
        const { visible } = usePopperjs(reference, popper, {
            ...props,
            trigger: toRef(props, "trigger"),
            forceShow: toRef(props, "forceShow"),
            disabled: toRef(props, "disabled"),
            delayOnMouseover: toRef(props, "delayOnMouseover"),
            delayOnMouseout: toRef(props, "delayOnMouseout"),
            onShow: () => emit("show"),
            onHide: () => emit("hide"),
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

        const handle =
            (event: Parameters<typeof emit>[0]) =>
            (...args: any[]) => {
                return emit(event, ...args);
            };

        return {
            visible,
            reference,
            popper,
            handle,
        };
    },
});
</script>

<style scoped lang="scss">
@import "theme/blue.scss";

.popper-element {
    z-index: 9999;
    border-radius: $border-radius-base;
}

.popper-element-dark {
    background: $brand-dark;
    color: $brand-light;
    max-width: 12rem;
    opacity: 0.95;
}

.popper-element-light {
    background: $white;
    color: $brand-dark;
    border: $border-default;
    box-shadow: 0 $border-radius-base $border-radius-base $brand-dark;
}

.popper-arrow,
.popper-arrow:before {
    height: 10px;
    width: 10px;
    position: absolute;
    z-index: -1;
}

.popper-arrow:before {
    background: $brand-dark;
    content: "";
    transform: rotate(45deg);
}

.popper-element[data-popper-placement^="top"] > .popper-arrow {
    bottom: -5px;
}

.popper-element[data-popper-placement^="bottom"] > .popper-arrow {
    top: -5px;
}

.popper-element[data-popper-placement^="left"] > .popper-arrow {
    right: -5px;
}

.popper-element[data-popper-placement^="right"] > .popper-arrow {
    left: -5px;
}
</style>

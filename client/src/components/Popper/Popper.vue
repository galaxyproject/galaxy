<template>
    <div>
        <component :is="referenceIs" v-bind="referenceProps" ref="reference">
            <slot name="reference" />
        </component>
        <component class="popper-box" v-show="visible" :is="popperIs" v-bind="popperProps" ref="popper">
            <slot />
        </component>
    </div>
</template>

<script lang="ts">
import { defineComponent, ref, toRef, computed, watch } from "vue";
import type { UnwrapRef, PropType } from "vue";
import { usePopperjs } from "./usePopper";
let popperUid = 0;

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
        disabled: Boolean,
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

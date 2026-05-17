<script setup lang="ts">
/**
 * Alert component that renders a bootstrap-styled alert div.
 * Replaces bootstrap-vue's BAlert with a Vue 3-friendly SFC that emits the same
 * `<div class="alert alert-{variant}">` markup the existing bootstrap CSS expects.
 */

import { computed, onBeforeUnmount, ref, watch } from "vue";

type AlertVariant = "info" | "warning" | "danger" | "success" | "primary" | "secondary" | "light" | "dark";
// `string & {}` keeps IDE autocomplete for the recommended variants while still accepting arbitrary
// strings (and null) -- mirrors BAlert's permissive prop typing so existing call sites don't have
// to cast. Null/empty variants fall back to the default `info` style.
type AlertVariantProp = AlertVariant | (string & {}) | null;
type AlertShow = boolean | number | string | null;

interface Props {
    /** Controls alert visibility */
    show?: AlertShow;
    /** Vue 2 default v-model value */
    value?: AlertShow;
    /** Vue 3 default v-model value */
    modelValue?: AlertShow;
    /** Bootstrap contextual variant */
    variant?: AlertVariantProp;
    /** Render a close button */
    dismissible?: boolean;
    /** Aria label for the dismiss button */
    dismissLabel?: string;
    /** Apply a fade transition on enter/leave */
    fade?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    show: true,
    value: undefined,
    modelValue: undefined,
    variant: "info",
    dismissible: false,
    dismissLabel: "Close",
    fade: false,
});

const emit = defineEmits<{
    (e: "dismissed"): void;
    (e: "dismiss-count-down", count: number): void;
    (e: "input", show: AlertShow): void;
    (e: "update:modelValue", show: AlertShow): void;
    (e: "update:show", show: AlertShow): void;
}>();

const variantClass = computed(() => `alert-${props.variant || "info"}`);

const boundShow = computed<AlertShow>(() => {
    if (props.value !== undefined) {
        return props.value;
    }
    if (props.modelValue !== undefined) {
        return props.modelValue;
    }
    return props.show;
});

const countDown = ref(0);
const localShow = ref(parseShow(boundShow.value));
let countDownTimeout: ReturnType<typeof setTimeout> | undefined;

function parseCountDown(show: AlertShow | undefined) {
    if (show === "" || show === null || show === undefined || typeof show === "boolean") {
        return 0;
    }

    const count = Number.parseInt(String(show), 10);
    return count > 0 ? count : 0;
}

function parseShow(show: AlertShow | undefined) {
    if (show === "" || show === true) {
        return true;
    }

    if (show === null || show === undefined || show === false) {
        return false;
    }

    const count = Number.parseInt(String(show), 10);
    if (!Number.isFinite(count) || count < 1) {
        return false;
    }

    return Boolean(show);
}

function hasNumericShow(show: AlertShow | undefined) {
    if (show === "" || show === null || show === undefined || typeof show === "boolean") {
        return false;
    }
    return Number.isFinite(Number(show));
}

function emitModel(show: AlertShow) {
    emit("input", show);
    emit("update:modelValue", show);
    emit("update:show", show);
}

function clearCountDownTimeout() {
    if (countDownTimeout) {
        clearTimeout(countDownTimeout);
        countDownTimeout = undefined;
    }
}

function setLocalShow(show: boolean) {
    const wasShown = localShow.value;
    localShow.value = show;

    if (!show && wasShown && (props.dismissible || hasNumericShow(boundShow.value))) {
        emit("dismissed");
    }
}

watch(
    boundShow,
    (next) => {
        const nextCountDown = parseCountDown(next);
        countDown.value = nextCountDown;
        setLocalShow(parseShow(next));

        if (!hasNumericShow(next)) {
            clearCountDownTimeout();
        }
    },
    { immediate: true },
);

watch(
    countDown,
    (next) => {
        clearCountDownTimeout();

        if (!hasNumericShow(boundShow.value)) {
            return;
        }

        emit("dismiss-count-down", next);
        emitModel(next);

        if (next > 0) {
            setLocalShow(true);
            countDownTimeout = setTimeout(() => {
                countDown.value -= 1;
            }, 1000);
        } else {
            setLocalShow(false);
        }
    },
    { immediate: true },
);

function onDismiss() {
    clearCountDownTimeout();
    if (hasNumericShow(boundShow.value)) {
        countDown.value = 0;
    } else {
        emitModel(false);
    }
    setLocalShow(false);
}

onBeforeUnmount(clearCountDownTimeout);
</script>

<script lang="ts">
export default {
    name: "GAlert",
};
</script>

<template>
    <Transition v-if="fade" name="g-alert-fade">
        <div
            v-if="localShow"
            class="alert"
            :class="[variantClass, { 'alert-dismissible': dismissible }]"
            role="alert"
            aria-live="polite"
            aria-atomic="true">
            <slot />
            <button v-if="dismissible" type="button" class="close" :aria-label="dismissLabel" @click="onDismiss">
                <span aria-hidden="true">&times;</span>
            </button>
        </div>
    </Transition>
    <div
        v-else-if="localShow"
        class="alert"
        :class="[variantClass, { 'alert-dismissible': dismissible }]"
        role="alert"
        aria-live="polite"
        aria-atomic="true">
        <slot />
        <button v-if="dismissible" type="button" class="close" :aria-label="dismissLabel" @click="onDismiss">
            <span aria-hidden="true">&times;</span>
        </button>
    </div>
</template>

<style scoped lang="scss">
.g-alert-fade-enter-active,
.g-alert-fade-leave-active {
    transition: opacity 0.15s linear;
}
.g-alert-fade-enter,
.g-alert-fade-enter-from,
.g-alert-fade-leave-to {
    opacity: 0;
}
</style>

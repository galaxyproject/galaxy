<script setup lang="ts">
import { useRouter } from "vue-router/composables";
import Popper from "@/components/Popper/Popper.vue";
import TextShort from "@/components/Common/TextShort.vue";

const router = useRouter();

interface Option {
    name: string;
    value: string;
}

export interface Props {
    id: string;
    title: string;
    icon?: string;
    isActive?: boolean;
    tooltip?: string;
    progressPercentage?: number;
    progressStatus?: string;
    options?: Option[];
    to?: string;
}

const props = withDefaults(defineProps<Props>(), {
    icon: "question",
    isActive: false,
    options: null,
    progressPercentage: 0,
    progressStatus: null,
    to: null,
    tooltip: null,
});

const emit = defineEmits<{
    (e: "click"): void;
}>();

function onClick(evt: MouseEvent): void {
    if (props.to) {
        router.push(props.to);
    }
    emit("click");
}
</script>

<template>
    <Popper reference-is="span" popper-is="span" placement="right">
        <template v-slot:reference>
            <div @click="onClick">
                <b-nav-item
                    :id="id"
                    class="position-relative my-1 p-2"
                    :class="{ 'nav-item-active': isActive }"
                    :aria-label="title | l">
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
                    <span class="position-relative">
                        <div class="nav-icon">
                            <icon :icon="icon" />
                        </div>
                        <TextShort :text="title" class="nav-title" />
                    </span>
                </b-nav-item>
            </div>
        </template>
        <div class="px-2 py-1">
            <small v-if="tooltip">{{ tooltip | l }}</small>
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

.nav-icon {
    @extend .nav-item;
    font-size: 1rem;
}

.nav-item {
    display: flex;
    align-items: center;
    align-content: center;
    justify-content: center;
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
    @extend .nav-item;
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

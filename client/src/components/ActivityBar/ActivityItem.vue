<script setup lang="ts">
import { useRouter } from "vue-router/composables";
import Popper from "components/Popper/Popper.vue";

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

function onClick(): void {
    if (props.to) {
        router.push(props.to);
    }
    emit("click");
}
</script>

<template>
    <div>
        <Popper reference-is="span" popper-is="span" placement="right">
            <template v-slot:reference>
                <b-nav-item
                    :id="id"
                    class="position-relative mb-1"
                    :class="{ 'nav-item-active': isActive }"
                    :aria-label="title | l"
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
                    <span class="position-relative">
                        <div class="nav-icon">
                            <Icon :icon="icon" />
                        </div>
                        <div class="nav-title">{{ title }}</div>
                    </span>
                </b-nav-item>
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
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

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

.nav-icon {
    @extend .nav-item;
    font-size: 1rem;
}

.nav-title {
    @extend .nav-item;
    margin-top: 0.7rem;
    margin-bottom: 0.3rem;
    line-height: 0rem;
    font-size: 0.7rem;
}

.nav-options {
    max-height: 20rem;
    overflow-x: hidden;
    overflow-y: auto;
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

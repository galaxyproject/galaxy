<script setup lang="ts">
import { BButton, BButtonGroup } from "bootstrap-vue";
import { computed } from "vue";

interface Props {
    title: string;
    goToAllTitle?: string;
    href?: string;
    /** Show GoTo button when on `href`? */
    goToOnHref?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    goToAllTitle: undefined,
    href: undefined,
});

const emit = defineEmits(["goToAll"]);

const hasGoToAll = computed(() => props.goToAllTitle && props.href);
</script>

<template>
    <div class="activity-panel" :data-description="props.title" aria-labelledby="activity-panel-heading">
        <div class="activity-panel-header">
            <nav unselectable="on" class="activity-panel-header-top">
                <h2 id="activity-panel-heading" v-localize class="activity-panel-heading h-sm">{{ props.title }}</h2>

                <BButtonGroup>
                    <slot name="header-buttons" />
                </BButtonGroup>
            </nav>

            <slot name="header" class="activity-panel-header-description" />
            <BButton
                v-if="hasGoToAll"
                class="activity-panel-footer"
                variant="primary"
                :data-description="`props.mainButtonText button`"
                :to="props.href"
                size="sm"
                @click="emit('goToAll')">
                {{ props.goToAllTitle }}
            </BButton>
        </div>

        <div class="activity-panel-body">
            <slot />
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

.activity-panel {
    height: 100%;
    display: flex;
    flex-flow: column;
    padding: 0.5rem 1rem;
    background-color: $brand-light;

    .activity-panel-header {
        padding-bottom: 0.5rem;

        .activity-panel-header-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            min-height: 2rem;

            .activity-panel-heading {
                margin: 0;
            }
        }
    }

    .activity-panel-body {
        display: flex;
        flex-direction: column;
        flex-grow: 1;
        overflow-y: auto;
        position: relative;
    }

    .activity-panel-footer {
        margin-top: 0.5rem;
        width: 100%;
        font-weight: bold;
    }
}
</style>

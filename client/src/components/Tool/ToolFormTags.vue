<script setup lang="ts">
import StatelessTags from "../TagsMultiselect/StatelessTags.vue";

const props = defineProps<{
    tags: string[];
}>();

const emit = defineEmits<{
    (e: "update:tags", value: string[]): void;
}>();
</script>

<template>
    <div class="ui-form-element section-row">
        <div class="ui-form-title">
            <span class="ui-form-title-text">
                <label for="tool-form-tags">Output Tags</label>
            </span>
        </div>
        <div id="tool-form-tags" class="ui-form-field">
            <StatelessTags :value="props.tags" placeholder="Add tags" @input="emit('update:tags', $event)" />
        </div>
        <span class="ui-form-info form-text text-muted">
            Enter tags to apply to the output datasets in your history (e.g., 'sample1'). Tags starting with '#' (e.g.,
            '#sample1') will propagate to datasets derived from these outputs. Tags help you organize and search your
            history.
        </span>
    </div>
</template>

<style lang="scss" scoped>
@import "../Form/_form-elements.scss";
</style>

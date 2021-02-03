<template>
    <StatelessTags :value="tags" @before-adding-tag="saveTag" @before-deleting-tag="deleteTag" />
</template>

<script>
// TODO: rewrite tags with provider component instead of dependency injection

import { Content } from "./model";
import { updateContentFields } from "./model/queries";
import { cacheContent } from "./caching";

import { StatelessTags } from "components/Tags";
import { createTag } from "components/Tags/model";

export default {
    components: {
        StatelessTags,
    },
    props: {
        content: { type: Content, required: true },
    },
    computed: {
        tags() {
            return this.content.tags;
        },
    },
    methods: {
        async saveTag({ tag, addTag }) {
            const newTag = createTag(tag);
            if (!newTag.valid) return;
            const tagSet = new Set(this.tags);
            tagSet.add(newTag.text);
            const tags = Array.from(tagSet);
            const ajaxResult = await updateContentFields(this.content, { tags });
            await cacheContent(ajaxResult);
            addTag(newTag);
        },
        async deleteTag({ tag, deleteTag }) {
            const doomedTag = createTag(tag);
            if (!doomedTag.valid) return;
            const tagSet = new Set([...this.tags]);
            tagSet.delete(doomedTag.text);
            const tags = Array.from(tagSet);
            const ajaxResult = await updateContentFields(this.content, { tags });
            await cacheContent(ajaxResult);
            deleteTag(tag);
        },
    },
};
</script>

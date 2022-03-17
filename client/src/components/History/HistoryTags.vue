<template>
    <Tags :tags="history.tags" :store-key="storeKey" :tag-service="historyTagService" :disabled="disabled" />
</template>

<script>
// TODO: Re-do tags as a provider instead of dependency injected service

import { History } from "./model";
import { updateHistoryFields } from "./model/queries";
import { Tags } from "components/Tags";
import { TagService } from "components/Tags/tagService";
import { createTag } from "components/Tags/model";

class HistoryTagService extends TagService {
    constructor(history) {
        super({
            id: history.id,
            itemClass: "History",
            context: "history-panel",
        });
        this.history = history;
    }

    async save(rawTag) {
        const tag = createTag(rawTag);
        const tagSet = new Set(this.history.tags);
        tagSet.add(tag.text);
        await this.saveHistoryTags(tagSet);
        return tag;
    }

    async delete(rawTag) {
        const tag = createTag(rawTag);
        const tagSet = new Set(this.history.tags);
        tagSet.delete(tag.text);
        await this.saveHistoryTags(tagSet);
        return tag;
    }

    async saveHistoryTags(rawTags) {
        // console.log("saveHistoryTags", rawTags);
        const tags = Array.from(rawTags);
        return await updateHistoryFields(this.history.id, { tags });
    }
}

export default {
    components: { Tags },
    props: {
        history: { type: History, required: true },
        disabled: { type: Boolean, required: false, default: false },
    },
    computed: {
        storeKey() {
            return `History-${this.history.id}`;
        },
        historyTagService() {
            return new HistoryTagService(this.history);
        },
    },
};
</script>

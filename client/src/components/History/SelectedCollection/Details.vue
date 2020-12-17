<template>
    <section class="history-details">
        <ClickToEdit
            :value="dsc.name"
            v-if="writable"
            @input="(name) => $emit('update:dsc', { name })"
            tag-name="h3"
            class="history-title mt-3"
            :tooltip-title="'Rename collection...' | localize"
        />
        <h3 v-else class="history-title mt-3">{{ dsc.name }}</h3>

        <p class="mt-1">
            <i class="fas fa-folder"></i>
            a {{ dsc.collectionType | localize }}
            {{ dsc.collectionCount | localize }}
        </p>

        <transition name="shutterfade">
            <ContentTags v-if="writable && showTags" :content="dsc" />
        </transition>

        <!-- <pre style="height:100px;overflow: scroll;">{{ dsc }}</pre> -->
    </section>
</template>

<script>
import { DatasetCollection } from "../model";
import ClickToEdit from "components/ClickToEdit";
import ContentTags from "../ContentTags";

export default {
    components: {
        ClickToEdit,
        ContentTags,
    },
    props: {
        dsc: { type: DatasetCollection, required: true },
        writable: { type: Boolean, required: true },
        showTags: { type: Boolean, required: true },
    },
};
</script>

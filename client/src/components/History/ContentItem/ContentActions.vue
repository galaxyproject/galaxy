<template>
    <div class="mb-1 clearfix">
        <div class="btn-group float-left">
            <b-button class="px-1" title="Download" size="sm" variant="link" @click.stop="$emit('save', item)">
                <span class="fa fa-save" />
            </b-button>
            <b-button class="px-1" title="Copy link" size="sm" variant="link" @click.stop="$emit('link', item)">
                <span class="fa fa-link" />
            </b-button>
            <b-button class="px-1" title="Dataset details" size="sm" variant="link" @click.stop="$emit('info', item)">
                <span class="fa fa-info-circle" />
            </b-button>
            <b-button class="px-1" title="Visualize" size="sm" variant="link" @click.stop="$emit('visualize', item)">
                <span class="fa fa-bar-chart-o" />
            </b-button>
            <b-button class="px-1" title="Help" size="sm" variant="link" @click.stop="$emit('help', item)">
                <span class="fa fa-question" />
            </b-button>
        </div>
        <div class="btn-group float-right">
            <b-button class="px-1" title="Edit tags" size="sm" variant="link" @click.stop="$emit('tags', item)">
                <span class="fa fa-tags" />
            </b-button>
            <b-button
                class="px-1"
                title="Edit annotation"
                size="sm"
                variant="link"
                @click.stop="$emit('annotation', item)">
                <span class="fa fa-comment" />
            </b-button>
        </div>
    </div>
</template>

<script>
import { copy as sendToClipboard } from "utils/clipboard";
import { absPath } from "utils/redirect";

export default {
    props: {
        item: { type: Object, required: true },
    },
    methods: {
        onCopyLink() {
            const relPath = this.item.download_url;
            const msg = this.localize("Link is copied to your clipboard");
            sendToClipboard(absPath(relPath), msg);
        },
    },
};
</script>

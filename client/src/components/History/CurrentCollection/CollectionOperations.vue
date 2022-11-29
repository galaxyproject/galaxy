<template>
    <section>
        <nav class="content-operations d-flex justify-content-between bg-secondary">
            <b-button-group>
                <b-button
                    title="Download Collection"
                    class="rounded-0 text-decoration-none"
                    size="sm"
                    variant="link"
                    :href="downloadUrl"
                    @click="onDownload">
                    <FontAwesomeIcon icon="fa-download" class="mr-1" />
                    <span>Download</span>
                </b-button>
            </b-button-group>
        </nav>
    </section>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faDownload } from "@fortawesome/free-solid-svg-icons";

library.add(faDownload);

export default {
    components: { FontAwesomeIcon },
    props: {
        dsc: { type: Object, required: true },
    },
    computed: {
        /** @return {String} */
        downloadUrl() {
            return `${this.dsc.url}/download`;
        },
    },
    methods: {
        onDownload() {
            window.location.href = this.downloadUrl;
        },
    },
};
</script>

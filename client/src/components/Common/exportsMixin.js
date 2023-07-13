//TODO: replace all usages of this with useFileSources composable

import LoadingSpan from "components/LoadingSpan";

import { getFileSources } from "@/components/FilesDialog/services";

export default {
    components: {
        LoadingSpan,
    },
    data() {
        return {
            initializingFileSources: true,
            hasWritableFileSources: false,
        };
    },
    computed: {
        initializeFileSourcesMessage() {
            return "Loading file sources configuration from Galaxy server.";
        },
    },
    methods: {
        async initializeFilesSources() {
            const fileSources = await new getFileSources();
            this.hasWritableFileSources = fileSources.some((fs) => fs.writable);
            this.initializingFileSources = false;
        },
    },
};

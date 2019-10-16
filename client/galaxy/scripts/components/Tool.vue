<template>
    <div :class="noSection ? 'toolTitleNoSection' : 'toolTitle'">
        <div>
            <a
                @click="open"
                :href="tool.link"
                :target="tool.target"
                :minsizehint="tool.min_width"
                :class="['tool-link', tool.id]"
            >
                <span class="labels">
                    <span
                        v-for="(label, index) in tool.labels"
                        :class="['badge', 'badge-primary', `badge-${label}`]"
                        :key="index"
                    >
                        {{ label }}
                    </span>
                </span>
                <span class="tool-old-link">{{ tool.name }}</span>
                {{ tool.description }}
            </a>
        </div>
    </div>
</template>

<script>
import { getGalaxyInstance } from "app"; // FIXME:
import ariaAlert from "utils/ariaAlert";

export default {
    name: "Tool",
    props: {
        tool: {
            type: Object,
            required: true
        },
        noSection: {
            type: Boolean,
            default: false
        }
    },
    methods: {
        open(e) {
            const formStyle = this.tool["form_style"];
            const Galaxy = getGalaxyInstance();

            if (this.tool.id === "upload1") {
                e.preventDefault();
                Galaxy.upload.show();
            } else if (formStyle === "regular") {
                e.preventDefault();
                Galaxy.router.push("/", {
                    tool_id: this.tool.id,
                    version: this.tool.version
                });
            }
            ariaAlert(`${this.tool.name} opened in galaxy center panel`);
        }
    },
    created() {}
};
</script>

<style scoped></style>

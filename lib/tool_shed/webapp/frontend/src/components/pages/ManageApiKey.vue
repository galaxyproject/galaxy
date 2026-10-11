<script setup lang="ts">
import { GButton, GFormInput, GFormLabel } from "@galaxyproject/galaxy-ui"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faCopy, faTrash, faArrowsRotate } from "@fortawesome/free-solid-svg-icons"
import { ref, computed } from "vue"
import PageContainer from "@/components/PageContainer.vue"
import PageHeader from "@/components/PageHeader.vue"
import { ToolShedApi } from "@/schema"
import { notify, copyAndNotify, notifyOnCatch, errorMessageAsString } from "@/util"
import ConfigFileContents from "@/components/ConfigFileContents.vue"

const apiKey = ref<string | null>(null)
const planemoConfig = computed(
    () =>
        `sheds:
  toolshed:
    key: ${apiKey.value}`,
)

async function copyKey() {
    if (apiKey.value) {
        copyAndNotify(apiKey.value, "API key copied to your clipboard")
    }
}

const params = { encoded_user_id: "current" }

async function init() {
    try {
        const { data } = await ToolShedApi().GET("/api/users/{encoded_user_id}/api_key", {
            params: {
                path: params,
            },
        })
        apiKey.value = data ?? null
    } catch (e) {
        notifyOnCatch(new Error(`Error fetching API key: ${errorMessageAsString(e)}`))
    }
}

async function deleteKey() {
    try {
        await ToolShedApi().DELETE("/api/users/{encoded_user_id}/api_key", {
            params: {
                path: params,
            },
        })

        apiKey.value = null
        notify("API key deactivated")
    } catch (e) {
        notifyOnCatch(new Error(`Error deactivating API key: ${errorMessageAsString(e)}`))
    }
}

async function recreateKey() {
    try {
        const { data } = await ToolShedApi().POST("/api/users/{encoded_user_id}/api_key", {
            params: {
                path: params,
            },
        })

        if (data) {
            apiKey.value = data
            notify("Re-generated API key")
        }
    } catch (e) {
        notifyOnCatch(new Error(`Error re-generating API key: ${errorMessageAsString(e)}`))
    }
}

void init()
</script>
<template>
    <page-container>
        <template #header>
            <page-header
                title="API key"
                subtitle="Your key for the Tool Shed web API -- Planemo uses it to publish repositories."
            />
        </template>
        <div class="api-key-layout">
            <section class="api-key-card shed-card">
                <h2 class="shed-section-title">Your API key</h2>
                <div class="api-key-row">
                    <GFormLabel title="API Key" class="api-key-field">
                        <GFormInput :model-value="apiKey" readonly class="api-key-input" />
                    </GFormLabel>
                    <div class="api-key-buttons">
                        <GButton icon-only outline title="Copy" aria-label="Copy API key" @click="copyKey">
                            <FontAwesomeIcon :icon="faCopy" />
                        </GButton>
                        <GButton
                            icon-only
                            outline
                            title="Regenerate"
                            aria-label="Regenerate API key"
                            @click="recreateKey"
                        >
                            <FontAwesomeIcon :icon="faArrowsRotate" />
                        </GButton>
                        <GButton
                            icon-only
                            outline
                            color="red"
                            title="Deactivate"
                            aria-label="Deactivate API key"
                            @click="deleteKey"
                        >
                            <FontAwesomeIcon :icon="faTrash" />
                        </GButton>
                    </div>
                </div>
                <p class="api-key-note">
                    This key is an alternate way into your account. Treat it with the same care as your password.
                </p>
            </section>
            <section class="api-key-card shed-card">
                <h2 class="shed-section-title">Planemo</h2>
                <p class="api-key-note">
                    Add this block to your Planemo configuration file, typically <code>~/.planemo.yml</code>.
                </p>
                <config-file-contents name=".planemo.yml" :contents="planemoConfig" what="Planemo configuration" />
            </section>
        </div>
    </page-container>
</template>

<style scoped>
.api-key-layout {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    max-width: 48rem;
}

.api-key-card {
    padding: 1.5rem;
}

.api-key-row {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    gap: 0.75rem;
}

.api-key-field {
    flex: 1 1 20rem;
}

.api-key-row :deep(.api-key-input) {
    width: 100%;
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    background: color-mix(in srgb, var(--shed-page-bg) 50%, white);
}

.api-key-buttons {
    display: flex;
    gap: 0.4rem;
}

.api-key-buttons :deep(.g-button) {
    width: 2.5rem;
    height: 2.5rem;
}

.api-key-note {
    margin: 1rem 0 0;
    color: var(--shed-muted);
}

.api-key-card .shed-section-title + .api-key-note {
    margin-top: 0;
}
</style>

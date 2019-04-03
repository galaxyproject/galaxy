<template>
    <b-form :validated="credential.isValid">

        <!-- user label -->
        <b-form-group 
            label="Description" 
            label-for="credentialDescription" 
            label-cols-lg="3">
            <b-form-input 
                id="credentialDescription"
                v-model="credential.description"
                :state="credential.fieldValid('description')"
                placeholder="Description (optional)"
                trim />
        </b-form-group>

        <!-- google-openidconnect -->
        <b-form-group 
            label="Identity Provider" 
            label-for="identityProvider"
            label-cols-lg="3"
            v-if="identityProviders.length > 1">
            <b-form-select 
                id="identityProvider"
                v-model="credential.authn_id"
                :state="credential.fieldValid('authn_id')"
                :options="identityProviders" />
        </b-form-group>
       
        <!-- aws/azure, etc -->
        <b-form-group 
            label="Resource Provider"
            label-for="resourceProvider"
            label-cols-lg="3">
            <b-form-select 
                id="resourceProvider"
                v-model="credential.resourceProvider"
                :state="credential.fieldValid('provider')"
                :options="resourceProviderOptions" />
        </b-form-group>
        
        <credential-config v-model="credential.config" />

        <footer>
            <b-button type="cancel"
                @click.prevent="$emit('delete', credential)">
                Delete Key
            </b-button>
            <b-button type="submit" 
                aria-label="Save Key"
                @click.prevent="$emit('save', credential)">
                Save This Key
            </b-button>
        </footer>

    </b-form>
</template>

<script>

import { Credential, ResourceProviders } from "./model";
import { getIdentityProviders } from "./model/service";
import CredentialConfig from "./CredentialConfig";

export default {
    components: {
        CredentialConfig
    },
    props: {
        value: { type: Credential, required: true }
    },
    data() {
        return {
            identityProviders: []
        }
    },
    computed: {
        credential() {
            return this.value;
        },
        // transformed for bootstrap component
        resourceProviderOptions() {
            let opts = Array.from(ResourceProviders.entries())
                .map(([value, o]) => ({ value, text: o.label }));
            return opts;
        },
        config() {
            return this.credential.config;
        }
    },
    created() {
        getIdentityProviders()
            .then(result => {
                if (!this.credential.authn_id && result.length == 1) {
                    this.credential.authn_id = result[0].authn_id;
                    this.credential.updateState();
                }
                this.identityProviders = result;
            });
    }
}

</script>

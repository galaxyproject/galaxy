<template>
    <div class="ui-thumbnails">
        <div class="ui-thumbnails-grid">
            <div v-for="plugin in plugins" class="ui-thumbnails-item">
                <table>
                    <tr>
                        <td>
                            <img v-if="plugin.logo" class="ui-thumbnails-image" :src="plugin.logo"/>
                            <div v-else class="ui-thumbnails-icon fa fa-eye"/>
                        </td>
                        <td>
                            <div class="ui-thumbnails-description-title ui-form-info">
                                {{ plugin.html }}
                            </div>
                            <div class="ui-thumbnails-description-text ui-form-info">
                                {{ plugin.description }}
                            </div>
                        </td>
                    </tr>
                </table>
            </div>
        </div>
    </div>
</template>
<script>
import axios from "axios";
export default {
    data() {
        return {
            plugins: []
        }
    },
    created() {
        axios.get(`${Galaxy.root}api/plugins`)
        .then(response => {
            this.plugins = response.data;
        })
        .catch(e => {
            alert(e);
        })
    }
};
</script>
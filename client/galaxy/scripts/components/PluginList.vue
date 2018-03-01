<template>
    <div class="ui-thumbnails">
        <div class="ui-thumbnails-grid">
            <div v-for="plugin in plugins">
                <table>
                    <tr class="ui-thumbnails-item" @click="select(plugin)">
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
                    <tr>
                        <td/>
                        <td>
                            <div v-if="files && plugin.name == name">
                                <div class="ui-form-info ui-bold">Select the dataset you would like to use:</div>
                                <div class="ui-select">
                                    <select class="select">
                                        <option v-for="file in files" :value="file.id">{{ file.name }}</option>
                                    </select>
                                    <div class="icon-dropdown fa fa-caret-down"/>
                                </div>
                                <button type="button" class="ui-button-default ui-float-left btn btn-primary">
                                    <i class="icon fa fa-check ui-margin-right"/>
                                    <span class="title">Create Visualization</span>
                                </button>
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
            plugins: [],
            files: [],
            name: null
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
    },
    methods: {
        select: function(plugin) {
            this.name = plugin.name;
            this.files = [{id: "1", name: "name"}, {id: "2", name: "name"}, {id: "3", name: "name"}, {id: "4", name: "name"}];
        }
    }
};
</script>
<style>
.ui-bold {
    font-weight: bold;
    margin-bottom: 5px;
}
.ui-float-left {
    float: left;
    margin-top:10px;
}
</style>
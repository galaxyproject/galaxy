<template>
    <div id="json-dump">
        <div v-show="Object" class="bco-stats">
            <h2 class="domain">JSON Dump</h2>
            <table>
            <tr v-for="(p_value, p_key) in item">
		  <td>{{ p_key }}</td><td>{{ p_value }}</td>
	    </tr>
	    </table>
	 </div>
    </div>
</template>

<script>
export default {
    name: "tree-item",
    props: {
    	item: Object
    },
};
</script>

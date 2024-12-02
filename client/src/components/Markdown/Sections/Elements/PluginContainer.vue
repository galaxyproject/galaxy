<script setup lang="ts">
import { ref, onMounted } from "vue";

// Define props
const props = defineProps<{
  pluginSrc: string;
}>();

// Reference for the plugin container
const pluginContainer = ref<HTMLDivElement | null>(null);

// Load the plugin script dynamically on mount
onMounted(() => {
  const container = pluginContainer.value;
  console.log("here");
  if (container) {
    container.id = "app"; // Ensure the container has id="app"

    const script = document.createElement("script");
    script.src = props.pluginSrc;
    script.async = true;

    // Handle script load success
    script.onload = () => {
      console.log(`Plugin loaded from: ${props.pluginSrc}`);
    };

    // Handle script load failure
    script.onerror = () => {
      console.error(`Failed to load plugin: ${props.pluginSrc}`);
    };

    // Append the script to the container
    container.appendChild(script);

  }
});
</script>

<template>
  <div>
    <!-- Scoped container for the plugin -->
    <div ref="pluginContainer"></div>
  </div>
</template>

<style scoped>
/* Add any styles you want specific to this component */
</style>

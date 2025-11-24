<template>
  <div>
    <h1>{{ message }}</h1>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const message = ref('Connecting to backend...');

onMounted(async () => {
  try {
    const response = await fetch('/api/');
    const data = await response.json();
    message.value = data.message;
  } catch (error) {
    console.error('Error fetching from backend:', error);
    message.value = 'Failed to connect to backend.';
  }
});
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}
</style>

<template>
  <div id="app">
    <header class="bg-dark text-light p-3 text-center">
      <h1>AI Stock Trader</h1>
    </header>
    <main class="container mt-4">
      <router-view />
    </main>
  </div>
</template>

<script>
export default {
  name: 'App',
  mounted() {
    // Clean up old service workers that might be cached by the browser
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.getRegistrations().then(function(registrations) {
        for(let registration of registrations) {
          registration.unregister();
          console.log('Old service worker unregistered.');
        }
      });
    }
  }
}
</script>

<style>
/* You can add global styles here */
body {
  background-color: #f8f9fa;
}
</style>
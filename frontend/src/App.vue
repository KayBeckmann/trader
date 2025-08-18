<template>
  <div id="app">
    <header class="bg-dark text-light p-3">
      <div class="container d-flex justify-content-between align-items-center">
        <h1 class="mb-0">AI Stock Trader</h1>
        <nav>
          <router-link to="/" class="text-white me-3">Home</router-link>
          <router-link to="/wiki" class="text-white">Wiki</router-link>
        </nav>
      </div>
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
nav a.router-link-exact-active {
  text-decoration: underline;
}
</style>

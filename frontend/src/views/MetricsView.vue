<template>
  <div class="metrics">
    <h1>System Metrics</h1>

    <div v-if="error" class="alert alert-danger">{{ error }}</div>

    <div class="row" v-if="metrics">
      <div class="col-md-6">
        <div class="card mb-3">
          <div class="card-header">Health</div>
          <div class="card-body">
            <p><strong>Market Open:</strong> <span :class="metrics.market_open ? 'text-success' : 'text-danger'">{{ metrics.market_open ? 'YES' : 'NO' }}</span></p>
            <p><strong>Database:</strong> <span :class="metrics.database.ok ? 'text-success' : 'text-danger'">{{ metrics.database.ok ? 'OK' : 'ERROR' }}</span></p>
            <p><strong>Redis:</strong> <span :class="metrics.redis.ok ? 'text-success' : 'text-danger'">{{ metrics.redis.ok ? 'OK' : 'ERROR' }}</span></p>
          </div>
        </div>

        <div class="card mb-3">
          <div class="card-header">Stock Prices</div>
          <div class="card-body">
            <p><strong>Total Rows:</strong> {{ metrics.stock_prices.total ?? 0 }}</p>
            <p><strong>Symbols:</strong> {{ metrics.stock_prices.symbols ?? 0 }}</p>
            <p><strong>Last Timestamp:</strong> {{ metrics.stock_prices.last_timestamp_iso || '-' }}</p>
          </div>
        </div>
      </div>

      <div class="col-md-6">
        <div class="card mb-3">
          <div class="card-header">Training</div>
          <div class="card-body">
            <p><strong>Open:</strong> {{ metrics.training.open ?? 0 }}</p>
            <p><strong>Closed:</strong> {{ metrics.training.closed ?? 0 }}</p>
            <p><strong>Processed:</strong> {{ metrics.training.processed ?? 0 }}</p>
          </div>
        </div>

        <div class="card mb-3">
          <div class="card-header">Trades</div>
          <div class="card-body">
            <p><strong>Open:</strong> {{ metrics.trades.open ?? 0 }}</p>
            <p><strong>Closed:</strong> {{ metrics.trades.closed ?? 0 }}</p>
            <p><strong>Last Closed:</strong> {{ metrics.trades.last_closed_timestamp_iso || '-' }}</p>
          </div>
        </div>

        <div class="card mb-3">
          <div class="card-header">Predictions</div>
          <div class="card-body">
            <p><strong>Long:</strong> {{ metrics.predictions.long_count ?? 0 }}</p>
            <p><strong>Short:</strong> {{ metrics.predictions.short_count ?? 0 }}</p>
            <p><strong>Last Published:</strong> {{ metrics.predictions.last_published_iso || '-' }}</p>
          </div>
        </div>
      </div>
    </div>

    <div class="card" v-if="metrics">
      <div class="card-header">Raw JSON</div>
      <div class="card-body">
        <pre style="white-space: pre-wrap;">{{ metrics }}</pre>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'

export default {
  name: 'MetricsView',
  setup() {
    const metrics = ref(null)
    const error = ref('')

    const load = async () => {
      try {
        const res = await fetch('/api/metrics')
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        metrics.value = await res.json()
      } catch (e) {
        error.value = String(e)
      }
    }

    onMounted(() => {
      load()
      // Refresh periodically
      setInterval(load, 30000)
    })

    return { metrics, error }
  }
}
</script>

<style scoped>
.metrics {
  text-align: left;
}
</style>


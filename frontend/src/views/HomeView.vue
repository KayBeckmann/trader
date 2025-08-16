<template>
  <div class="home">
    <div class="alert alert-warning" role="alert">
      <strong>Forschungsprojekt und KEINE Anlageberatung</strong>
    </div>
    <!-- Market Status -->
    <div class="card mb-4">
      <div class="card-body">
        <h5 class="card-title">Market Status</h5>
        <p class="card-text">
          The market is currently <span :class="isMarketOpen ? 'text-success' : 'text-danger'">{{ marketStatus }}</span>.
        </p>
        <small class="text-muted">Market hours: {{ marketHours.open_hour_utc }}:00 - {{ marketHours.close_hour_utc }}:00 UTC (Mon-Fri)</small>
      </div>
    </div>

    <!-- Predictions -->
    <div class="row">
      <div class="col-md-6">
        <div class="card">
          <div class="card-header bg-success text-white">
            Top 10 Long
          </div>
          <ul class="list-group list-group-flush">
            <li v-for="stock in predictions.long" :key="stock" class="list-group-item">{{ stock }}</li>
            <li v-if="!predictions.long.length" class="list-group-item text-muted">No predictions available.</li>
          </ul>
        </div>
      </div>
      <div class="col-md-6">
        <div class="card">
          <div class="card-header bg-danger text-white">
            Top 10 Short
          </div>
          <ul class="list-group list-group-flush">
            <li v-for="stock in predictions.short" :key="stock" class="list-group-item">{{ stock }}</li>
            <li v-if="!predictions.short.length" class="list-group-item text-muted">No predictions available.</li>
          </ul>
        </div>
      </div>
    </div>

    <!-- P/L Chart -->
    <div class="card mt-4">
      <div class="card-body">
        <h5 class="card-title">Profit/Loss History</h5>
        <div v-if="chartData.datasets[0].data.length > 1">
           <LineChart :chartData="chartData" style="height: 300px"/>
        </div>
        <p v-else class="card-text text-muted">Not enough trade data to display a chart.</p>
      </div>
    </div>

  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue';
import LineChart from '../components/LineChart.vue';

export default {
  name: 'HomeView',
  components: { LineChart },
  setup() {
    const predictions = ref({ long: [], short: [] });
    const trades = ref([]);
    const marketHours = ref({});
    const isMarketOpen = ref(false);

    const marketStatus = computed(() => isMarketOpen.value ? 'OPEN' : 'CLOSED');

    // Process trade data for the chart
    const chartData = computed(() => {
      const sortedTrades = [...trades.value].sort((a, b) => a.timestamp - b.timestamp);
      let cumulativePl = 0;
      const data = [];
      const labels = [];

      // Start with a zero point
      data.push(0);
      labels.push('Start');

      sortedTrades.forEach(trade => {
        cumulativePl += trade.profit_loss;
        data.push(cumulativePl);
        labels.push(new Date(trade.timestamp * 1000).toLocaleTimeString());
      });

      return {
        labels,
        datasets: [
          {
            label: 'Cumulative P/L',
            backgroundColor: '#f87979',
            borderColor: '#f87979',
            data: data,
            fill: false,
            tension: 0.1
          }
        ]
      };
    });

    // Fetch initial data from REST APIs
    const fetchData = async () => {
      try {
        // Fetch predictions
        const predRes = await fetch('/api/predictions');
        predictions.value = await predRes.json();

        // Fetch trades
        const tradesRes = await fetch('/api/trades');
        trades.value = await tradesRes.json();

        // Fetch market hours
        const hoursRes = await fetch('/api/market-hours');
        marketHours.value = await hoursRes.json();
        checkMarketStatus();

      } catch (error) {
        console.error("Error fetching data:", error);
      }
    };

    // Check if market is open based on fetched hours
    const checkMarketStatus = () => {
      const now = new Date();
      const nowUtc = {
        day: now.getUTCDay() -1, // Monday is 0 in this logic
        hour: now.getUTCHours()
      };
      if (marketHours.value.market_days_utc.includes(nowUtc.day)) {
        if (nowUtc.hour >= marketHours.value.open_hour_utc && nowUtc.hour < marketHours.value.close_hour_utc) {
          isMarketOpen.value = true;
          return;
        }
      }
      isMarketOpen.value = false;
    };

    // Setup WebSocket connection
    const setupWebSocket = () => {
      const ws = new WebSocket(`ws://${window.location.host}/ws/predictions`);

      ws.onmessage = (event) => {
        console.log("WebSocket message received:", event.data);
        predictions.value = JSON.parse(event.data);
      };

      ws.onopen = () => {
        console.log("WebSocket connection established.");
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };

       ws.onclose = () => {
        console.log("WebSocket connection closed. Reconnecting in 5 seconds...");
        setTimeout(setupWebSocket, 5000);
      };
    };

    onMounted(() => {
      fetchData();
      setupWebSocket();
      // Check market status every minute
      setInterval(checkMarketStatus, 60000);
    });

    return {
      predictions,
      trades,
      marketHours,
      isMarketOpen,
      marketStatus,
      chartData
    };
  }
}
</script>

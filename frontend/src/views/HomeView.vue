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
        <small class="text-muted">
          Trading windows ({{ localTimezone }}): {{ localMarketHours }}
        </small>
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
    const marketHours = ref({ markets: [] });
    const isMarketOpen = ref(false);

    const marketStatus = computed(() => isMarketOpen.value ? 'OPEN' : 'CLOSED');

    const localTimezone = computed(() => {
      return Intl.DateTimeFormat().resolvedOptions().timeZone;
    });

    const localMarketHours = computed(() => {
      const markets = marketHours.value.markets || [];
      if (!markets.length) {
        return '...';
      }
      const now = new Date();
      const year = now.getUTCFullYear();
      const month = now.getUTCMonth();
      const day = now.getUTCDate();
      const options = { hour: '2-digit', minute: '2-digit' };

      return markets.map(market => {
        const openUtc = new Date(Date.UTC(year, month, day, market.open_utc.hour, market.open_utc.minute));
        const closeUtc = new Date(Date.UTC(year, month, day, market.close_utc.hour, market.close_utc.minute));
        const openLocal = openUtc.toLocaleTimeString([], options);
        const closeLocal = closeUtc.toLocaleTimeString([], options);
        return `${market.name}: ${openLocal} - ${closeLocal}`;
      }).join(' | ');
    });

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
      const markets = marketHours.value.markets || [];
      if (!markets.length) {
        isMarketOpen.value = false;
        return;
      }

      const now = new Date();
      const nowDay = now.getUTCDay() === 0 ? 6 : now.getUTCDay() - 1; // Align with Python weekday()
      const nowTotalMinutes = now.getUTCHours() * 60 + now.getUTCMinutes();

      isMarketOpen.value = markets.some(market => {
        if (!market.days.includes(nowDay)) {
          return false;
        }
        const openTotalMinutes = market.open_utc.hour * 60 + market.open_utc.minute;
        const closeTotalMinutes = market.close_utc.hour * 60 + market.close_utc.minute;
        return nowTotalMinutes >= openTotalMinutes && nowTotalMinutes < closeTotalMinutes;
      });
    };

    // Setup WebSocket connection
    const setupWebSocket = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(`${protocol}//${window.location.host}/ws/predictions`);

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
      chartData,
      localMarketHours,
      localTimezone
    };
  }
}
</script>

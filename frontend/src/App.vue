<template>
  <div id="app">
    <h1>Trader Dashboard</h1>
    <div class="connection-status" :class="connectionStatus">
      {{ connectionStatusText }}
    </div>
    <div class="container">
      <div class="knn-lists">
        <div class="knn-list">
          <h2>Top 10 Long</h2>
          <ul v-if="topLong.length > 0">
            <li v-for="item in topLong" :key="item.id || item.symbol">
              <div class="stock-info">
                <div class="stock-main">
                  <span class="stock-rank">{{ item.rank }}.</span>
                  <span class="stock-symbol">{{ item.symbol }}</span>
                  <span v-if="item.name" class="stock-name">{{ item.name }}</span>
                </div>
                <div class="stock-details">
                  <span v-if="item.isin" class="stock-isin">ISIN: {{ item.isin }}</span>
                  <span v-if="item.score" class="score">({{ (item.score * 100).toFixed(1) }}%)</span>
                </div>
              </div>
            </li>
          </ul>
          <div v-else class="no-data">
            <p>{{ dataLoading ? 'Loading...' : 'No predictions available' }}</p>
            <small v-if="!dataLoading">System needs time to collect data and train the model.</small>
          </div>
        </div>
        <div class="knn-list">
          <h2>Top 10 Short</h2>
          <ul v-if="topShort.length > 0">
            <li v-for="item in topShort" :key="item.id || item.symbol">
              <div class="stock-info">
                <div class="stock-main">
                  <span class="stock-rank">{{ item.rank }}.</span>
                  <span class="stock-symbol">{{ item.symbol }}</span>
                  <span v-if="item.name" class="stock-name">{{ item.name }}</span>
                </div>
                <div class="stock-details">
                  <span v-if="item.isin" class="stock-isin">ISIN: {{ item.isin }}</span>
                  <span v-if="item.score" class="score">({{ (item.score * 100).toFixed(1) }}%)</span>
                </div>
              </div>
            </li>
          </ul>
          <div v-else class="no-data">
            <p>{{ dataLoading ? 'Loading...' : 'No predictions available' }}</p>
            <small v-if="!dataLoading">System needs time to collect data and train the model.</small>
          </div>
        </div>
      </div>
      <div class="chart-container">
        <h2>Trade History</h2>
        <div v-if="hasTradeData" class="chart-wrapper">
          <Line :data="chartData" :options="chartOptions" />
        </div>
        <div v-else class="no-data chart-no-data">
          <p>{{ tradesLoading ? 'Loading trade history...' : 'No trade history available' }}</p>
          <small v-if="!tradesLoading">Trades will appear here after positions are closed (typically after 1 hour or when profit/loss targets are reached).</small>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import axios from 'axios';
import { Line } from 'vue-chartjs';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
  Filler,
} from 'chart.js';
import 'chartjs-adapter-date-fns';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
  Filler
);

const topLong = ref([]);
const topShort = ref([]);
const dataLoading = ref(true);
const tradesLoading = ref(true);
const chartData = ref({
  datasets: [],
});
const chartOptions = ref({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index',
    intersect: false,
  },
  scales: {
    x: {
      type: 'time',
      time: {
        unit: 'hour',
        displayFormats: {
          hour: 'MMM d, HH:mm'
        }
      },
      title: {
        display: true,
        text: 'Time'
      }
    },
    y: {
      beginAtZero: true,
      title: {
        display: true,
        text: 'P&L ($)'
      }
    },
  },
  plugins: {
    tooltip: {
      callbacks: {
        afterTitle: function(context) {
          const dataPoint = context[0].raw;
          if (dataPoint && dataPoint.symbol) {
            return `${dataPoint.symbol} (${dataPoint.type})`;
          }
          return '';
        },
        label: function(context) {
          const value = context.parsed.y;
          const sign = value >= 0 ? '+' : '';
          return `${context.dataset.label}: ${sign}$${value.toFixed(2)}`;
        }
      }
    },
    legend: {
      position: 'top',
    }
  }
});

// WebSocket connection state
const wsConnected = ref(false);
const wsReconnecting = ref(false);
let ws = null;
let reconnectTimeout = null;
let heartbeatInterval = null;

const connectionStatus = computed(() => {
  if (wsConnected.value) return 'connected';
  if (wsReconnecting.value) return 'reconnecting';
  return 'disconnected';
});

const connectionStatusText = computed(() => {
  if (wsConnected.value) return 'Live';
  if (wsReconnecting.value) return 'Reconnecting...';
  return 'Disconnected';
});

const fetchTopKnnResults = async () => {
  try {
    const response = await axios.get('/api/knn/top');
    topLong.value = response.data.long.map((item, index) => ({
      ...item,
      rank: item.rank || index + 1
    }));
    topShort.value = response.data.short.map((item, index) => ({
      ...item,
      rank: item.rank || index + 1
    }));
  } catch (error) {
    console.error('Error fetching KNN results:', error);
  } finally {
    dataLoading.value = false;
  }
};

const fetchTradeHistory = async () => {
  try {
    const response = await axios.get('/api/trades');
    const trades = response.data;
    // Filter out trades without closed_at date and sort by date
    const closedTrades = trades
      .filter(trade => trade.closed_at)
      .sort((a, b) => new Date(a.closed_at) - new Date(b.closed_at));

    // Calculate cumulative P&L
    let cumulativePnL = 0;
    const cumulativeData = closedTrades.map(trade => {
      const tradePnL = (trade.exit_price - trade.entry_price) * (trade.type === 'long' ? 1 : -1);
      cumulativePnL += tradePnL;
      return {
        x: new Date(trade.closed_at),
        y: cumulativePnL,
        symbol: trade.symbol,
        type: trade.type,
        pnl: tradePnL
      };
    });

    // Also prepare individual trade P&L data
    const individualPnL = closedTrades.map(trade => ({
      x: new Date(trade.closed_at),
      y: (trade.exit_price - trade.entry_price) * (trade.type === 'long' ? 1 : -1),
      symbol: trade.symbol,
      type: trade.type
    }));

    chartData.value = {
      datasets: [
        {
          label: 'Cumulative P&L',
          backgroundColor: 'rgba(33, 150, 243, 0.2)',
          borderColor: '#2196F3',
          fill: true,
          tension: 0.1,
          data: cumulativeData,
        },
        {
          label: 'Per Trade P&L',
          backgroundColor: individualPnL.map(d => d.y >= 0 ? 'rgba(76, 175, 80, 0.7)' : 'rgba(244, 67, 54, 0.7)'),
          borderColor: individualPnL.map(d => d.y >= 0 ? '#4CAF50' : '#F44336'),
          type: 'bar',
          data: individualPnL,
          barThickness: 8,
        },
      ],
    };
  } catch (error) {
    console.error('Error fetching trade history:', error);
  } finally {
    tradesLoading.value = false;
  }
};

const hasTradeData = computed(() => {
  return chartData.value.datasets.length > 0 &&
         chartData.value.datasets[0].data &&
         chartData.value.datasets[0].data.length > 0;
});

const connectWebSocket = () => {
  // Determine WebSocket URL based on current location
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/predictions`;

  try {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected');
      wsConnected.value = true;
      wsReconnecting.value = false;

      // Start heartbeat
      heartbeatInterval = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        }
      }, 25000);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // Ignore heartbeat messages
        if (data.type === 'heartbeat') return;

        // Update predictions if we received valid data
        if (data.long && data.short) {
          topLong.value = data.long.map((item, index) => ({
            symbol: item.symbol,
            score: item.score,
            rank: index + 1,
            name: item.name,
            isin: item.isin,
            wkn: item.wkn
          }));
          topShort.value = data.short.map((item, index) => ({
            symbol: item.symbol,
            score: item.score,
            rank: index + 1,
            name: item.name,
            isin: item.isin,
            wkn: item.wkn
          }));
          console.log('Received real-time predictions update');
        }
      } catch (e) {
        // Not JSON, might be a pong response
        if (event.data !== 'pong') {
          console.log('Received non-JSON message:', event.data);
        }
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      wsConnected.value = false;
      clearInterval(heartbeatInterval);

      // Attempt to reconnect after 5 seconds
      wsReconnecting.value = true;
      reconnectTimeout = setTimeout(() => {
        console.log('Attempting to reconnect...');
        connectWebSocket();
      }, 5000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  } catch (error) {
    console.error('Failed to create WebSocket connection:', error);
    wsReconnecting.value = true;
    reconnectTimeout = setTimeout(connectWebSocket, 5000);
  }
};

const disconnectWebSocket = () => {
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout);
    reconnectTimeout = null;
  }
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval);
    heartbeatInterval = null;
  }
  if (ws) {
    ws.close();
    ws = null;
  }
};

onMounted(() => {
  // Initial data fetch
  fetchTopKnnResults();
  fetchTradeHistory();

  // Connect WebSocket for real-time updates
  connectWebSocket();

  // Fallback polling for trade history (less frequent since WebSocket handles predictions)
  setInterval(() => {
    fetchTradeHistory();
    // Also fetch KNN results as fallback if WebSocket is disconnected
    if (!wsConnected.value) {
      fetchTopKnnResults();
    }
  }, 60000);
});

onUnmounted(() => {
  disconnectWebSocket();
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

.connection-status {
  position: fixed;
  top: 10px;
  right: 10px;
  padding: 5px 15px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: bold;
}

.connection-status.connected {
  background-color: #4caf50;
  color: white;
}

.connection-status.reconnecting {
  background-color: #ff9800;
  color: white;
}

.connection-status.disconnected {
  background-color: #f44336;
  color: white;
}

.container {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
  padding: 20px;
}

@media (min-width: 768px) {
  .container {
    grid-template-columns: 1fr 1fr;
  }
}

.knn-lists {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.knn-list ul {
  list-style: none;
  padding: 0;
  text-align: left;
}

.knn-list li {
  padding: 8px 12px;
  margin: 4px 0;
  background-color: #f5f5f5;
  border-radius: 4px;
}

.stock-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stock-main {
  display: flex;
  align-items: baseline;
  gap: 6px;
  flex-wrap: wrap;
}

.stock-rank {
  font-weight: bold;
  color: #333;
  min-width: 20px;
}

.stock-symbol {
  font-weight: bold;
  color: #2196F3;
}

.stock-name {
  color: #666;
  font-size: 0.9em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 150px;
}

.stock-details {
  display: flex;
  justify-content: space-between;
  font-size: 0.85em;
  padding-left: 26px;
}

.stock-isin {
  color: #888;
  font-family: monospace;
}

.knn-list li .score {
  color: #666;
  font-size: 0.9em;
}

.chart-container {
  height: 400px;
}

.chart-wrapper {
  height: 350px;
}

.no-data {
  padding: 20px;
  text-align: center;
  color: #666;
  background-color: #f9f9f9;
  border-radius: 8px;
  border: 1px dashed #ddd;
}

.no-data p {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #888;
}

.no-data small {
  font-size: 12px;
  color: #aaa;
}

.chart-no-data {
  height: 200px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}
</style>

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
          <ul>
            <li v-for="item in topLong" :key="item.id || item.symbol">
              {{ item.rank }}. {{ item.symbol }}
              <span v-if="item.score" class="score">({{ (item.score * 100).toFixed(1) }}%)</span>
            </li>
          </ul>
        </div>
        <div class="knn-list">
          <h2>Top 10 Short</h2>
          <ul>
            <li v-for="item in topShort" :key="item.id || item.symbol">
              {{ item.rank }}. {{ item.symbol }}
              <span v-if="item.score" class="score">({{ (item.score * 100).toFixed(1) }}%)</span>
            </li>
          </ul>
        </div>
      </div>
      <div class="chart-container">
        <h2>Trade History</h2>
        <Line :data="chartData" :options="chartOptions" />
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
  Title,
  Tooltip,
  Legend,
  TimeScale,
} from 'chart.js';
import 'chartjs-adapter-date-fns';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
);

const topLong = ref([]);
const topShort = ref([]);
const chartData = ref({
  datasets: [],
});
const chartOptions = ref({
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    x: {
      type: 'time',
      time: {
        unit: 'hour',
      },
    },
    y: {
      beginAtZero: true,
    },
  },
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
  }
};

const fetchTradeHistory = async () => {
  try {
    const response = await axios.get('/api/trades');
    const trades = response.data;
    const profitAndLoss = trades.map(trade => ({
      x: new Date(trade.closed_at),
      y: (trade.exit_price - trade.entry_price) * (trade.type === 'long' ? 1 : -1),
    }));

    chartData.value = {
      datasets: [
        {
          label: 'Profit/Loss',
          backgroundColor: '#f87979',
          data: profitAndLoss,
        },
      ],
    };
  } catch (error) {
    console.error('Error fetching trade history:', error);
  }
};

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
            rank: index + 1
          }));
          topShort.value = data.short.map((item, index) => ({
            symbol: item.symbol,
            score: item.score,
            rank: index + 1
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

.knn-list li .score {
  float: right;
  color: #666;
  font-size: 0.9em;
}

.chart-container {
  height: 400px;
}
</style>

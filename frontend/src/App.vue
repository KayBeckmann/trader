<template>
  <div id="app">
    <h1>Trader Dashboard</h1>
    <div class="container">
      <div class="knn-lists">
        <div class="knn-list">
          <h2>Top 10 Long</h2>
          <ul>
            <li v-for="item in topLong" :key="item.id">
              {{ item.rank }}. {{ item.symbol }}
            </li>
          </ul>
        </div>
        <div class="knn-list">
          <h2>Top 10 Short</h2>
          <ul>
            <li v-for="item in topShort" :key="item.id">
              {{ item.rank }}. {{ item.symbol }}
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
import { ref, onMounted } from 'vue';
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

const fetchTopKnnResults = async () => {
  try {
    const response = await axios.get('/api/knn/top');
    topLong.value = response.data.long;
    topShort.value = response.data.short;
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

onMounted(() => {
  fetchTopKnnResults();
  fetchTradeHistory();
  setInterval(() => {
    fetchTopKnnResults();
    fetchTradeHistory();
  }, 60000); // Refresh every minute
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

.chart-container {
  height: 400px;
}
</style>

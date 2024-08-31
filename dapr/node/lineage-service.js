const express = require('express');
const bodyParser = require('body-parser');
const promClient = require('prom-client');

const app = express();
app.use(bodyParser.json());

const port = 3004;  // Change this line to match the port in docker-compose.yml

// Prometheus setup
const register = new promClient.Registry();
promClient.collectDefaultMetrics({ register });

const lineageRequestCounter = new promClient.Counter({
  name: 'lineage_requests_total',
  help: 'Total number of lineage requests',
  labelNames: ['operation']
});
register.registerMetric(lineageRequestCounter);

// Mock functions for lineage operations
const recordLineage = async (dataset, data) => {
  console.log(`Recording lineage for dataset ${dataset}:`, JSON.stringify(data));
  return { id: Math.floor(Math.random() * 1000), timestamp: new Date().toISOString(), ...data };
};

const getLineage = async (dataset) => {
  console.log(`Retrieving lineage for dataset: ${dataset}`);
  return {
    dataset: dataset,
    lineage: [
      { input: "raw_data", output: dataset, transformation: "extract_transform_load" },
      { input: dataset, output: "analytics_table", transformation: "aggregate" }
    ]
  };
};

// Record lineage endpoint
app.post('/recordLineage', async (req, res) => {
  try {
    const { dataset, lineageData } = req.body;
    console.log('Received lineage data for dataset:', dataset, lineageData);
    const result = await recordLineage(dataset, lineageData);
    lineageRequestCounter.inc({ operation: 'record' });
    res.status(200).json({ message: 'Lineage recorded successfully', data: result });
  } catch (error) {
    console.error('Error recording lineage:', error);
    res.status(500).json({ message: 'Failed to record lineage', error: error.message });
  }
});

// Get lineage endpoint
app.get('/getLineage', async (req, res) => {
  try {
    const { dataset } = req.query;
    const lineageData = await getLineage(dataset);
    lineageRequestCounter.inc({ operation: 'get' });
    res.status(200).json(lineageData);
  } catch (error) {
    console.error('Error getting lineage:', error);
    res.status(500).json({ message: 'Failed to get lineage', error: error.message });
  }
});

// Prometheus metrics endpoint
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});

app.listen(port, () => console.log(`Lineage service listening on port ${port}!`));
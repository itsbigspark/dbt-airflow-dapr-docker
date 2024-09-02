const express = require('express');
const bodyParser = require('body-parser');
const promClient = require('prom-client');

const app = express();
app.use(bodyParser.json());

const port = 3002;

// Prometheus setup
const register = new promClient.Registry();
promClient.collectDefaultMetrics({ register });

const configRequestCounter = new promClient.Counter({
  name: 'config_requests_total',
  help: 'Total number of configuration requests',
  labelNames: ['config_type']
});
register.registerMetric(configRequestCounter);

// Mock functions to get configurations
const getProcessConfig = async () => {
  return {
    max_retries: 3,
    timeout: 3600,
    parallel_processes: 4,
    log_level: "INFO"
  };
};

const getDAGConfig = async (dagId) => {
  return {
    dag_id: dagId,
    schedule_interval: "0 * * * *",
    start_date: "2023-01-01",
    catchup: false,
    default_args: {
      owner: "data_team",
      retries: 1,
      retry_delay: 300
    }
  };
};

// Add this new function to get dataset configuration
const getDatasetConfig = async (dataset) => {
  return {
    name: dataset,
    source: "s3://data-lake/raw/",
    destination: "s3://data-warehouse/processed/",
    schema: ["id", "name", "value", "timestamp"],
    partitions: ["date"]
  };
};

// Get process config endpoint
app.get('/config', async (req, res) => {
  try {
    const config = await getProcessConfig();
    configRequestCounter.inc({ config_type: 'process' });
    res.status(200).json(config);
  } catch (error) {
    console.error('Error getting process configuration:', error);
    res.status(500).json({ message: 'Failed to get process configuration', error: error.message });
  }
});

// Get DAG config endpoint
app.get('/dagConfig', async (req, res) => {
  const { dagId } = req.query;
  try {
    const config = await getDAGConfig(dagId);
    configRequestCounter.inc({ config_type: 'dag' });
    res.status(200).json(config);
  } catch (error) {
    console.error('Error getting DAG configuration:', error);
    res.status(500).json({ message: 'Failed to get DAG configuration', error: error.message });
  }
});

// Add this new endpoint for getting dataset config
app.get('/datasetConfig', async (req, res) => {
  const { dataset } = req.query;
  try {
    const config = await getDatasetConfig(dataset);
    configRequestCounter.inc({ config_type: 'dataset' });
    res.status(200).json(config);
  } catch (error) {
    console.error('Error getting dataset configuration:', error);
    res.status(500).json({ message: 'Failed to get dataset configuration', error: error.message });
  }
});

// Prometheus metrics endpoint
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});

app.listen(port, () => console.log(`Airflow config service listening on port ${port}!`));
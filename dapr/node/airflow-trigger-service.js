const express = require('express');
const bodyParser = require('body-parser');
const promClient = require('prom-client');

const app = express();
app.use(bodyParser.json());

const port = 3001;

// Prometheus setup
const register = new promClient.Registry();
promClient.collectDefaultMetrics({ register });

const dagTriggerCounter = new promClient.Counter({
  name: 'dag_triggers_total',
  help: 'Total number of DAG triggers',
  labelNames: ['dag_id']
});
register.registerMetric(dagTriggerCounter);

// Mock function to trigger Airflow DAG
const triggerAirflowDAG = async (dagId, conf) => {
  console.log("Triggering Airflow DAG: " + dagId + " with conf:", JSON.stringify(conf));
  return { status: "success", execution_date: new Date().toISOString() };
};

// Trigger DAG endpoint
app.post('/triggerDag', async (req, res) => {
  const { dagId, conf } = req.body;
  console.log('Received request to trigger DAG:', dagId, 'with config:', conf);
  
  try {
    const response = await triggerAirflowDAG(dagId, conf);
    dagTriggerCounter.inc({ dag_id: dagId });
    res.status(200).json({ message: 'DAG triggered successfully', data: response });
  } catch (error) {
    console.error('Error triggering DAG:', error);
    res.status(500).json({ message: 'Failed to trigger DAG', error: error.message });
  }
});

// Prometheus metrics endpoint
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});

app.listen(port, () => console.log(`Airflow trigger service listening on port ${port}!`));
// ------------------------------------------------------------
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.
// ------------------------------------------------------------

const express = require('express');
const bodyParser = require('body-parser');
require('isomorphic-fetch');

const { MeterProvider } = require('@opentelemetry/sdk-metrics');
const { PrometheusExporter } = require('@opentelemetry/exporter-prometheus');

const app = express();
app.use(bodyParser.json());

const daprPort = process.env.DAPR_HTTP_PORT || 3500;
const stateStoreName = `statestore`;
const stateUrl = `http://localhost:${daprPort}/v1.0/state/${stateStoreName}`;
const port = 3000;

// Add this new function to generate a correlation ID
const generateCorrelationId = () => {
  return `corr-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

// Mock services with test data
const triggerAirflowDAG = async (dagId, conf) => {
  console.log("Triggering Airflow DAG: " + dagId + " with conf:", JSON.stringify(conf));
  return { status: "success", execution_date: new Date().toISOString() };
};

// Modify the recordEvent function
const recordEvent = async (eventType, details) => {
  console.log(`Recording ${eventType} event for dataset ${details.dataset}:`, JSON.stringify(details));
  const stateKey = `${details.dataset}/${details.correlationId}`;
  const eventValue = { 
    id: Math.floor(Math.random() * 1000), 
    timestamp: new Date().toISOString(), 
    type: eventType,
    ...details 
  };
  
  try {
    // First, get existing events for this dataset and correlationId
    let existingEvents = await getEvents(details.dataset, details.correlationId);
    
    // Ensure existingEvents is an array
    if (!Array.isArray(existingEvents)) {
      existingEvents = [];
    }

    // Add the new event
    existingEvents.push(eventValue);

    // Save the updated list of events
    const state = [{
      key: stateKey,
      value: JSON.stringify(existingEvents)
    }];

    const response = await fetch(stateUrl, {
      method: 'POST',
      body: JSON.stringify(state),
      headers: {
        'Content-Type': 'application/json'
      }
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    console.log(`Successfully recorded event for ${stateKey}`);
    return eventValue;
  } catch (error) {
    console.error(`Failed to record state for ${eventType} event:`, error);
    throw error;
  }
};

const recordLineage = async (dataset, data) => {
  console.log(`Recording lineage for dataset ${dataset}:`, JSON.stringify(data));
  return { id: Math.floor(Math.random() * 1000), timestamp: new Date().toISOString(), ...data };
};

// Modify the getEvents function
const getEvents = async (dataset, correlationId) => {
  console.log(`Retrieving events for dataset: ${dataset}, correlationId: ${correlationId}`);
  try {
    const stateKey = `${dataset}/${correlationId}`;
    const response = await fetch(`${stateUrl}/${stateKey}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      if (response.status === 404) {
        // If no events found, return an empty array
        return [];
      }
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const events = await response.json();
    return Array.isArray(events) ? events : [];
  } catch (error) {
    console.error(`Error retrieving events for dataset ${dataset}, correlationId ${correlationId}:`, error);
    return [];
  }
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

const getProcessConfig = async () => {
  console.log("Retrieving process configuration");
  return {
    max_retries: 3,
    timeout: 3600,
    parallel_processes: 4,
    log_level: "INFO"
  };
};

const getDatasetConfig = async (dataset) => {
  console.log(`Retrieving configuration for dataset: ${dataset}`);
  return {
    name: dataset,
    source: "s3://data-lake/raw/",
    destination: "s3://data-warehouse/processed/",
    schema: ["id", "name", "value", "timestamp"],
    partitions: ["date"]
  };
};

const getDAGConfig = async (dagId) => {
  console.log(`Retrieving configuration for DAG: ${dagId}`);
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

// New endpoint for getting configuration
app.get('/config', async (req, res) => {
  const span = tracer.startSpan('get_config');
  try {
    const config = await getProcessConfig();
    res.status(200).send(config);
  } catch (error) {
    console.error('Error getting configuration:', error);
    res.status(500).send({ message: 'Failed to get configuration', error: error.message });
  } finally {
    span.end();
  }
});

// Modify the /recordEvent endpoint
app.post('/recordEvent', async (req, res) => {
  try {
    const eventData = req.body;
    console.log('Received event:', eventData);
    const recordedEvent = await recordEvent(eventData.status, eventData);
    res.status(200).send({ message: 'Event recorded successfully', event: recordedEvent });
  } catch (error) {
    console.error('Error recording event:', error);
    res.status(500).send({ message: 'Failed to record event', error: error.message });
  }
});

// Modify the /getEvents endpoint
app.get('/getEvents', async (req, res) => {
  try {
    const { dataset, correlationId } = req.query;
    if (!dataset || !correlationId) {
      return res.status(400).send({ message: 'Dataset and correlationId parameters are required' });
    }
    const events = await getEvents(dataset, correlationId);
    console.log(`Retrieved events for dataset ${dataset}, correlationId ${correlationId}:`, events);
    res.status(200).send(events);
  } catch (error) {
    console.error('Error getting events:', error);
    res.status(500).send({ message: 'Failed to get events', error: error.toString() });
  }
});

// Add a new endpoint to generate a correlation ID
app.get('/generateCorrelationId', (req, res) => {
  const correlationId = generateCorrelationId();
  res.status(200).send({ correlationId });
});

// New endpoint for recording lineage
app.post('/recordLineage', async (req, res) => {
  try {
    const { dataset, lineageData } = req.body;
    console.log('Received lineage data for dataset:', dataset, lineageData);
    await recordLineage(dataset, lineageData);
    res.status(200).send({ message: 'Lineage recorded successfully' });
  } catch (error) {
    console.error('Error recording lineage:', error);
    res.status(500).send({ message: 'Failed to record lineage', error: error.message });
  }
});

// New endpoint for getting lineage
app.get('/getLineage', async (req, res) => {
  try {
    const { dataset } = req.query;
    const lineageData = await getLineage(dataset);
    res.status(200).send(lineageData);
  } catch (error) {
    console.error('Error getting lineage:', error);
    res.status(500).send({ message: 'Failed to get lineage', error: error.message });
  }
});

// New endpoint for triggering DAG
app.post('/triggerDag', async (req, res) => {
  try {
    const { dagId, conf } = req.body;
    console.log('Received request to trigger DAG:', dagId, 'with config:', conf);
    const response = await triggerAirflowDAG(dagId, conf);
    res.status(200).send({ message: 'DAG triggered successfully', data: response });
  } catch (error) {
    console.error('Error triggering DAG:', error);
    res.status(500).send({ message: 'Failed to trigger DAG', error: error.message });
  }
});

// New endpoint for getting dataset config
app.get('/datasetConfig', async (req, res) => {
  try {
    const { dataset } = req.query;
    const config = await getDatasetConfig(dataset);
    res.status(200).send(config);
  } catch (error) {
    console.error('Error getting dataset config:', error);
    res.status(500).send({ message: 'Failed to get dataset config', error: error.message });
  }
});

// New endpoint for getting DAG config
app.get('/dagConfig', async (req, res) => {
  try {
    const { dagId } = req.query;
    const config = await getDAGConfig(dagId);
    res.status(200).send(config);
  } catch (error) {
    console.error('Error getting DAG config:', error);
    res.status(500).send({ message: 'Failed to get DAG config', error: error.message });
  }
});

// Set up the Prometheus exporter
const prometheusExporter = new PrometheusExporter({
  port: 9091, // This matches the port specified in docker-compose.yml
  startServer: true,
});

// Create and register MeterProvider
const meterProvider = new MeterProvider();
meterProvider.addMetricReader(prometheusExporter);

// Create a meter
const meter = meterProvider.getMeter('nodeapp');

// Create some example metrics
const requestCounter = meter.createCounter('requests_total', {
  description: 'Total number of requests',
});

// Use the metrics in your routes
app.use((req, res, next) => {
  requestCounter.add(1, { method: req.method, path: req.path });
  next();
});

app.listen(port, '0.0.0.0', () => console.log(`Node App listening on port ${port}!`));

const opentelemetry = require('@opentelemetry/api');
const { NodeTracerProvider } = require('@opentelemetry/sdk-trace-node');
const { SimpleSpanProcessor } = require('@opentelemetry/sdk-trace-base');
const { ZipkinExporter } = require('@opentelemetry/exporter-zipkin');

const provider = new NodeTracerProvider();
const exporter = new ZipkinExporter({
  url: 'http://otel-collector:9411/api/v2/spans',
  serviceName: 'nodeapp'
});

provider.addSpanProcessor(new SimpleSpanProcessor(exporter));
provider.register();

const tracer = opentelemetry.trace.getTracer('nodeapp');

// Use tracer.startSpan() to create spans in your application
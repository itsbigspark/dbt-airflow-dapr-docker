// ------------------------------------------------------------
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.
// ------------------------------------------------------------

const express = require('express');
const bodyParser = require('body-parser');
require('isomorphic-fetch');

const app = express();
app.use(bodyParser.json());

const daprPort = process.env.DAPR_HTTP_PORT || 3500;
const stateStoreName = `statestore`;
const stateUrl = `http://localhost:${daprPort}/v1.0/state/${stateStoreName}`;
const port = 3000;

// Mock services with test data
const triggerAirflowDAG = async (dagId, conf) => {
  console.log("Triggering Airflow DAG: " + dagId + " with conf:", JSON.stringify(conf));
  return { status: "success", execution_date: new Date().toISOString() };
};

const recordEvent = async (eventType, details) => {
  console.log(`Recording ${eventType} event:`, JSON.stringify(details));
  return { id: Math.floor(Math.random() * 1000), timestamp: new Date().toISOString(), ...details };
};

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

// app.get('/order', (_req, res) => {
    
//     fetch(`${stateUrl}/order`)
//         .then((response) => {
//             if (!response.ok) {
//                 throw "Could not get state.";
//             }

//             return response.text();
//         }).then((orders) => {
//             res.send(orders);
//             console.log(orders);
//         }).catch((error) => {
//             console.log(error);
//             res.status(500).send({message: error});
//         });
// });

// app.post('/neworder', async (req, res) => {
//     const data = req.body.data;
//     const orderId = data.orderId;
//     console.log("Got a new order! Order ID: " + orderId);

//     try {
//         await triggerAirflowDAG();
//         await recordEvent('start', { orderId });

//         const state = [{
//             key: "order",
//             value: data
//         }];

//         const response = await fetch(stateUrl, {
//             method: "POST",
//             body: JSON.stringify(state),
//             headers: {
//                 "Content-Type": "application/json"
//             }
//         });

//         if (!response.ok) {
//             throw "Failed to persist state.";
//         }

//         console.log("Successfully persisted state.");
//         await recordLineage('order', { input: 'neworder', output: 'statestore', transformation: 'persist' });
//         await recordEvent('end', { orderId, status: 'success' });
//         res.status(200).send();
//     } catch (error) {
//         console.log(error);
//         await recordEvent('end', { orderId, status: 'error', message: error });
//         res.status(500).send({message: error});
//     }
// });

// New endpoint for getting configuration
app.get('/config', async (req, res) => {
  try {
    const config = await getProcessConfig();
    res.status(200).send(config);
  } catch (error) {
    console.error('Error getting configuration:', error);
    res.status(500).send({ message: 'Failed to get configuration', error: error.message });
  }
});

// New endpoint for recording events
app.post('/recordEvent', async (req, res) => {
  try {
    const eventData = req.body;
    console.log('Received event:', eventData);
    await recordEvent(eventData.status, eventData);
    res.status(200).send({ message: 'Event recorded successfully' });
  } catch (error) {
    console.error('Error recording event:', error);
    res.status(500).send({ message: 'Failed to record event', error: error.message });
  }
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

app.listen(port, () => console.log(`Node App listening on port ${port}!`));
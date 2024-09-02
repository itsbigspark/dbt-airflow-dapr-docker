const express = require('express');
const bodyParser = require('body-parser');
require('isomorphic-fetch');
const promClient = require('prom-client');

const app = express();
app.use(bodyParser.json());

const daprPort = process.env.DAPR_HTTP_PORT || 3500;
const stateStoreName = `statestore`;
const stateUrl = `http://localhost:${daprPort}/v1.0/state/${stateStoreName}`;
const port = 3000;

// Prometheus setup
const register = new promClient.Registry();
promClient.collectDefaultMetrics({ register });

const eventCounter = new promClient.Counter({
  name: 'audit_events_total',
  help: 'Total number of audit events',
  labelNames: ['event_type']
});
register.registerMetric(eventCounter);

// Record event
app.post('/recordEvent', async (req, res) => {
  const eventData = req.body;
  console.log('Recording event:', eventData);
  
  try {
    const state = [{
      key: `${eventData.dataset}/${eventData.correlationId}/${Date.now()}`,
      value: JSON.stringify(eventData)
    }];

    const response = await fetch(stateUrl, {
      method: 'POST',
      body: JSON.stringify(state),
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    eventCounter.inc({ event_type: eventData.status });
    res.status(200).json({ message: 'Event recorded successfully', event: eventData });
  } catch (error) {
    console.error('Error recording event:', error);
    res.status(500).json({ message: 'Failed to record event', error: error.message });
  }
});

// Get events
app.get('/getEvents', async (req, res) => {
  const { dataset, correlationId } = req.query;
  console.log(`Retrieving events for dataset: ${dataset}, correlationId: ${correlationId}`);

  try {
    const response = await fetch(`${stateUrl}/${dataset}/${correlationId}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const events = await response.json();
    res.status(200).json(events);
  } catch (error) {
    console.error('Error retrieving events:', error);
    res.status(500).json({ message: 'Failed to retrieve events', error: error.message });
  }
});

// Prometheus metrics endpoint
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});

app.listen(port, () => console.log(`Audit service listening on port ${port}!`));
const express = require('express');
const bodyParser = require('body-parser');

const app = express();
app.use(bodyParser.json());

const port = 3003;

// Function to generate a correlation ID
const generateCorrelationId = () => {
  return `corr-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

// Endpoint to generate a correlation ID
app.get('/generateCorrelationId', (req, res) => {
  const correlationId = generateCorrelationId();
  res.status(200).send({ correlationId });
});

app.listen(port, '0.0.0.0', () => console.log(`Management Service listening on port ${port}!`));
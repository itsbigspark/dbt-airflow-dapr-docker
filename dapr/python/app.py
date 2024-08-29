import json
import random
import time
from datetime import datetime

import requests

# Dapr configuration
dapr_port = 3500
base_url = f"http://localhost:{dapr_port}/v1.0/invoke/nodeapp/method"

def call_endpoint(endpoint, method='GET', data=None):
    url = f"{base_url}/{endpoint}"
    try:
        if method == 'GET':
            response = requests.get(url, params=data, timeout=5)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling {endpoint}: {e}")
        print(f"URL: {url}")
        print(f"Method: {method}")
        print(f"Data: {data}")
        return None

def simulate_data_processing(dataset_config):
    if dataset_config is None:
        print("Error: dataset_config is None")
        return 0

    print(f"Processing data for dataset: {dataset_config.get('name', 'Unknown')}")
    print(f"Source: {dataset_config.get('source', 'Unknown')}")
    print(f"Destination: {dataset_config.get('destination', 'Unknown')}")
    print(f"Schema: {', '.join(dataset_config.get('schema', []))}")
    print(f"Partitions: {', '.join(dataset_config.get('partitions', []))}")
    
    # Simulate processing time based on dataset size
    processing_time = random.uniform(0.5, 5.0)
    time.sleep(processing_time)
    
    processed_rows = random.randint(1000, 1000000)
    print(f"Processed {processed_rows} rows in {processing_time:.2f} seconds")
    
    return processed_rows

def data_engineering_pipeline():
    # Step 1: Get process configuration
    process_config = call_endpoint('config')
    if process_config is None:
        print("Failed to get process configuration. Exiting pipeline.")
        return

    # Step 2: Get dataset configuration
    dataset = "example_dataset"
    dataset_config = call_endpoint('datasetConfig', data={'dataset': dataset})
    if dataset_config is None:
        print(f"Failed to get dataset configuration for {dataset}. Exiting pipeline.")
        return

    print(f"Dataset Config for {dataset}:", json.dumps(dataset_config, indent=2))

    # Step 3: Record start event
    start_event = {
        'status': 'start',
        'pipeline': 'data_engineering_pipeline',
        'timestamp': datetime.now().isoformat()
    }
    start_event_response = call_endpoint('recordEvent', method='POST', data=start_event)
    print("Recorded start event:", json.dumps(start_event_response, indent=2))

    # Step 4: Simulate data processing
    processed_rows = simulate_data_processing(dataset_config)

    # Step 5: Record lineage
    lineage_data = {
        'input': dataset_config['source'],
        'output': dataset_config['destination'],
        'transformation': 'data_engineering_pipeline',
        'rows_processed': processed_rows
    }
    lineage_response = call_endpoint('recordLineage', method='POST', data={'dataset': dataset, 'lineageData': lineage_data})
    print("Recorded lineage:", json.dumps(lineage_response, indent=2))

    # Step 6: Trigger Airflow DAG
    dag_id = 'example_dag'
    dag_config = call_endpoint('dagConfig', data={'dagId': dag_id})
    print(f"DAG Config for {dag_id}:", json.dumps(dag_config, indent=2))

    dag_conf = {
        'dataset': dataset,
        'processed_at': datetime.now().isoformat(),
        'rows_processed': processed_rows
    }
    dag_trigger_response = call_endpoint('triggerDag', method='POST', data={'dagId': dag_id, 'conf': dag_conf})
    print(f"Triggered DAG: {dag_id}", json.dumps(dag_trigger_response, indent=2))

    # Step 7: Get lineage information
    lineage_info = call_endpoint('getLineage', data={'dataset': dataset_config['destination']})
    print("Lineage Information:", json.dumps(lineage_info, indent=2))

    # Step 8: Record end event
    end_event = {
        'status': 'end',
        'pipeline': 'data_engineering_pipeline',
        'timestamp': datetime.now().isoformat(),
        'result': 'success',
        'rows_processed': processed_rows
    }
    end_event_response = call_endpoint('recordEvent', method='POST', data=end_event)
    print("Recorded end event:", json.dumps(end_event_response, indent=2))

if __name__ == "__main__":
    print(f"Dapr sidecar URL: {base_url}")
    while True:
        print("\nStarting Data Engineering Pipeline...")
        data_engineering_pipeline()
        print("Pipeline completed. Waiting before next run...")
        time.sleep(random.randint(5, 15))  # Wait for 5-15 seconds before next run
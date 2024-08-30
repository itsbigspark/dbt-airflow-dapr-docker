import json
import random
import time
from datetime import datetime

import plotly.graph_objects as go
import requests
import streamlit as st

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
        st.error(f"Error calling {endpoint}: {e}")
        st.error(f"URL: {url}")
        st.error(f"Method: {method}")
        st.error(f"Data: {data}")
        return None

def simulate_data_processing(dataset_config):
    if dataset_config is None:
        st.error("Error: dataset_config is None")
        return 0

    st.write(f"Processing data for dataset: {dataset_config.get('name', 'Unknown')}")
    st.write(f"Source: {dataset_config.get('source', 'Unknown')}")
    st.write(f"Destination: {dataset_config.get('destination', 'Unknown')}")
    st.write(f"Schema: {', '.join(dataset_config.get('schema', []))}")
    st.write(f"Partitions: {', '.join(dataset_config.get('partitions', []))}")
    
    # Simulate processing time based on dataset size
    processing_time = random.uniform(0.5, 5.0)
    time.sleep(processing_time)
    
    processed_rows = random.randint(1000, 1000000)
    st.write(f"Processed {processed_rows} rows in {processing_time:.2f} seconds")
    
    return processed_rows

def data_engineering_pipeline():
    # Step 1: Get process configuration
    process_config = call_endpoint('config')
    if process_config is None:
        st.error("Failed to get process configuration. Exiting pipeline.")
        return

    # Step 2: Get dataset configuration
    dataset = "transactions_raw"
    dataset_config = call_endpoint('datasetConfig', data={'dataset': dataset})
    if dataset_config is None:
        st.error(f"Failed to get dataset configuration for {dataset}. Exiting pipeline.")
        return

    st.write(f"Dataset Config for {dataset}:", json.dumps(dataset_config, indent=2))

    # Step 3: Record start event
    start_event = {
        'status': 'start',
        'pipeline': 'data_engineering_pipeline',
        'timestamp': datetime.now().isoformat(),
        'dataset': dataset
    }
    start_event_response = call_endpoint('recordEvent', method='POST', data=start_event)
    st.write("Recorded start event:", json.dumps(start_event_response, indent=2))

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
    st.write("Recorded lineage:", json.dumps(lineage_response, indent=2))

    # Step 6: Trigger Airflow DAG
    dag_id = 'example_dag'
    dag_config = call_endpoint('dagConfig', data={'dagId': dag_id})
    st.write(f"DAG Config for {dag_id}:", json.dumps(dag_config, indent=2))

    dag_conf = {
        'dataset': dataset,
        'processed_at': datetime.now().isoformat(),
        'rows_processed': processed_rows
    }
    dag_trigger_response = call_endpoint('triggerDag', method='POST', data={'dagId': dag_id, 'conf': dag_conf})
    st.write(f"Triggered DAG: {dag_id}", json.dumps(dag_trigger_response, indent=2))

    # Step 7: Get lineage information
    lineage_info = call_endpoint('getLineage', data={'dataset': dataset_config['destination']})
    st.write("Lineage Information:", json.dumps(lineage_info, indent=2))

    # Step 8: Record end event
    end_event = {
        'status': 'end',
        'pipeline': 'data_engineering_pipeline',
        'timestamp': datetime.now().isoformat(),
        'result': 'success',
        'rows_processed': processed_rows,
        'dataset': dataset
    }
    end_event_response = call_endpoint('recordEvent', method='POST', data=end_event)
    st.write("Recorded end event:", json.dumps(end_event_response, indent=2))

    # Add a progress bar for pipeline execution
    progress_bar = st.progress(0)
    for i in range(8):
        # Simulate step execution
        time.sleep(0.5)
        progress_bar.progress((i + 1) / 8)

# Streamlit app
st.set_page_config(page_title="Data Engineering Pipeline", layout="wide")

# Custom CSS for better styling
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
    }
    .stProgress .st-bo {
        background-color: #4CAF50;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 Data Engineering Pipeline")

# Create two columns for the main layout
col1, col2 = st.columns([2, 1])

with col1:
    st.header("Pipeline Execution")
    if st.button("🏁 Start Data Engineering Pipeline"):
        st.write("Starting Data Engineering Pipeline...")
        data_engineering_pipeline()
        st.success("Pipeline completed successfully!")

    st.subheader("📊 Audit Logs")
    dataset = st.text_input("Dataset", "transactions_raw")
    if st.button("Get Lineage Information"):
        lineage_info = call_endpoint('getLineage', data={'dataset': dataset})
        if lineage_info and isinstance(lineage_info, dict):
            fig = go.Figure(data=[go.Sankey(
                node = dict(
                  pad = 15,
                  thickness = 20,
                  line = dict(color = "black", width = 0.5),
                  label = [
                      lineage_info.get('input', 'Unknown Input'),
                      lineage_info.get('transformation', 'Unknown Transformation'),
                      lineage_info.get('output', 'Unknown Output')
                  ],
                  color = ["blue", "green", "red"]
                ),
                link = dict(
                  source = [0, 1],
                  target = [1, 2],
                  value = [1, 1]
              ))])
            fig.update_layout(title_text="Data Lineage", font_size=10)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No valid lineage information available.")

with col2:
    st.header("⚙️ Configuration")
    if st.button("Get Process Config"):
        process_config = call_endpoint('config')
        if process_config:
            st.json(process_config)
        else:
            st.warning("Failed to retrieve process configuration.")

    dag_id = st.text_input("DAG ID", "example_dag")
    if st.button("Get DAG Config"):
        dag_config = call_endpoint('dagConfig', data={'dagId': dag_id})
        if dag_config:
            st.json(dag_config)
        else:
            st.warning(f"Failed to retrieve DAG configuration for {dag_id}.")

    dataset = st.text_input("Dataset for Config", "transactions_raw")
    if st.button("Get Dataset Config"):
        dataset_config = call_endpoint('datasetConfig', data={'dataset': dataset})
        if dataset_config:
            st.json(dataset_config)
        else:
            st.warning(f"Failed to retrieve dataset configuration for {dataset}.")

    st.subheader("📝 Event Responses")
    if st.button("Show Event Responses"):
        dataset = "transactions_raw"  # You can make this dynamic if needed
        start_event_response = call_endpoint('recordEvent', method='POST', data={
            'status': 'start',
            'pipeline': 'data_engineering_pipeline',
            'timestamp': datetime.now().isoformat(),
            'dataset': dataset
        })
        end_event_response = call_endpoint('recordEvent', method='POST', data={
            'status': 'end',
            'pipeline': 'data_engineering_pipeline',
            'timestamp': datetime.now().isoformat(),
            'result': 'success',
            'rows_processed': random.randint(1000, 1000000),
            'dataset': dataset
        })
        if start_event_response and end_event_response:
            st.json({"Start Event Response": start_event_response, "End Event Response": end_event_response})
        else:
            st.warning("Failed to retrieve event responses.")
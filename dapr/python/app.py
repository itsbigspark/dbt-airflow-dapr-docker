import json
import logging
import random
import time
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# Dapr configuration
dapr_port = 3500
base_url = f"http://localhost:{dapr_port}/v1.0/invoke/nodeapp/method"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def call_endpoint(endpoint, method='GET', data=None):
    url = f"{base_url}/{endpoint}"
    try:
        logger.info(f"Calling endpoint: {url}")
        if method == 'GET':
            response = requests.get(url, params=data, timeout=5)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling {endpoint}: {e}")
        logger.error(f"URL: {url}")
        logger.error(f"Method: {method}")
        logger.error(f"Data: {data}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status code: {e.response.status_code}")
            logger.error(f"Response headers: {e.response.headers}")
            logger.error(f"Response text: {e.response.text}")
        st.error(f"Error calling {endpoint}: {e}")
        st.error(f"URL: {url}")
        st.error(f"Method: {method}")
        st.error(f"Data: {data}")
        return None

def simulate_data_processing(dataset_config):
    if dataset_config is None:
        st.error("Error: dataset_config is None")
        return 0

    # Create columns for structured output
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Dataset Information")
        st.write(f"**Name:** {dataset_config.get('name', 'Unknown')}")
        st.write(f"**Source:** {dataset_config.get('source', 'Unknown')}")
        st.write(f"**Destination:** {dataset_config.get('destination', 'Unknown')}")

    with col2:
        st.subheader("Schema and Partitions")
        st.write(f"**Schema:** {', '.join(dataset_config.get('schema', []))}")
        st.write(f"**Partitions:** {', '.join(dataset_config.get('partitions', []))}")

    # Simulate processing time based on dataset size
    processing_time = random.uniform(0.5, 5.0)
    processed_rows = random.randint(1000, 1000000)

    # Display processing progress
    progress_text = "Processing data..."
    my_bar = st.progress(0, text=progress_text)

    for percent_complete in range(100):
        time.sleep(processing_time / 100)
        my_bar.progress(percent_complete + 1, text=progress_text)

    # Display results
    st.success(f"Processed {processed_rows:,} rows in {processing_time:.2f} seconds")

    # Create a simple bar chart to visualize processed rows
    chart_data = pd.DataFrame({
        'Metric': ['Processed Rows'],
        'Value': [processed_rows]
    })
    st.bar_chart(chart_data, x='Metric', y='Value', use_container_width=True)

    return processed_rows

def generate_correlation_id():
    return call_endpoint('generateCorrelationId')['correlationId']

def record_event(event_type, details, dataset, process_start_time, correlation_id):
    event_data = {
        'status': event_type,
        'pipeline': 'data_engineering_pipeline',
        'timestamp': datetime.now().isoformat(),
        'dataset': dataset,
        'process_start_time': process_start_time,
        'correlationId': correlation_id,
        **details
    }
    recorded_event = call_endpoint('recordEvent', method='POST', data=event_data)
    if recorded_event:
        st.success(f"Event recorded: {event_type}")
        with st.expander(f"{event_type.capitalize()} Event", expanded=False):
            st.json(recorded_event)
    else:
        st.error(f"Failed to record event: {event_type}")
    return recorded_event

def get_events(dataset, correlation_id):
    events = call_endpoint('getEvents', data={'dataset': dataset, 'correlationId': correlation_id})
    if events is None:
        st.error(f"Failed to retrieve events for dataset: {dataset}, correlationId: {correlation_id}")
        return []
    return events

def data_engineering_pipeline():
    # Generate a correlation ID at the start of processing
    correlation_id = generate_correlation_id()
    st.info(f"Correlation ID for this run: {correlation_id}")

    # Add a progress bar for pipeline execution
    progress_bar = st.progress(0)
    
    # Step 1: Get process configuration
    process_config = call_endpoint('config')
    if (process_config is None):
        st.error("Failed to get process configuration. Exiting pipeline.")
        return
    progress_bar.progress(1 / 8)

    # Step 2: Get dataset configuration
    dataset = "transactions_raw"
    dataset_config = call_endpoint('datasetConfig', data={'dataset': dataset})
    if (dataset_config is None):
        st.error(f"Failed to get dataset configuration for {dataset}. Exiting pipeline.")
        return
    progress_bar.progress(2 / 8)
    time.sleep(1)  # Slow down processing

    with st.expander("Dataset Configuration", expanded=True):
        st.json(dataset_config)

    # Step 3: Record start event
    process_start_time = datetime.now().isoformat()
    start_event = record_event('start', {'dataset': dataset}, dataset, process_start_time, correlation_id)
    with st.expander("Start Event", expanded=True):
        st.json(start_event)
    progress_bar.progress(3 / 8)
    time.sleep(1)  # Slow down processing

    # Step 4: Trigger Airflow DAG
    dag_id = 'dag_'+dataset
    dag_config = call_endpoint('dagConfig', data={'dagId': dag_id})
    # with st.expander("DAG Configuration", expanded=True):
    #     st.json(dag_config)

    # Record DAG configuration event
    dag_config_event = record_event('dag_config_retrieved', {
        'dag_id': dag_id,
        'dag_config': dag_config
    }, dataset, process_start_time, correlation_id)
    # with st.expander("DAG Config Event", expanded=True):
    #     st.json(dag_config_event)

    dag_conf = {
        'dataset': dataset,
        'processed_at': datetime.now().isoformat(),
        'rows_processed': 0  # Placeholder, will be updated after processing
    }
    dag_trigger_response = call_endpoint('triggerDag', method='POST', data={'dagId': dag_id, 'conf': dag_conf})
    # with st.expander("DAG Trigger", expanded=True):
    #     st.json(dag_trigger_response)
    progress_bar.progress(4 / 8)
    time.sleep(1)  # Slow down processing

    # Record DAG trigger event
    dag_trigger_event = record_event('dag_triggered', {
        'dag_id': dag_id,
        'dag_conf': dag_conf,
        'dag_trigger_response': dag_trigger_response
    }, dataset, process_start_time, correlation_id)
    # with st.expander("DAG Trigger Event", expanded=True):
    #     st.json(dag_trigger_event)

    # Step 5: Simulate data processing
    with st.expander("Data Processing", expanded=True):
        processed_rows = simulate_data_processing(dataset_config)
    progress_bar.progress(5 / 8)
    time.sleep(1)  # Slow down processing

    # Step 6: Record lineage
    lineage_data = {
        'input': dataset_config['source'],
        'output': dataset_config['destination'],
        'transformation': 'data_engineering_pipeline',
        'rows_processed': processed_rows
    }
    lineage_response = call_endpoint('recordLineage', method='POST', data={'dataset': dataset, 'lineageData': lineage_data})
    with st.expander("Lineage Recording", expanded=True):
        st.json(lineage_response)
    progress_bar.progress(6 / 8)
    time.sleep(1)  # Slow down processing

    # Record lineage event
    lineage_event = record_event('lineage_recorded', {
        'dataset': dataset,
        'lineage_data': lineage_data
    }, dataset, process_start_time, correlation_id)
    # with st.expander("Lineage Event", expanded=True):
    #     st.json(lineage_event)

    # Step 7: Get lineage information
    lineage_info = call_endpoint('getLineage', data={'dataset': dataset_config['destination']})
    # with st.expander("Lineage Information", expanded=True):
    #     st.json(lineage_info)
    progress_bar.progress(7 / 8)
    time.sleep(1)  # Slow down processing

    # Step 8: Record end event
    end_event = record_event('end', {
        'result': 'success',
        'rows_processed': processed_rows,
        'dataset': dataset
    }, dataset, process_start_time, correlation_id)
    # with st.expander("End Event", expanded=True):
    #     st.json(end_event)
    progress_bar.progress(8 / 8)
    time.sleep(1)  # Slow down processing

    return correlation_id

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
        correlation_id = data_engineering_pipeline()
        st.success(f"Pipeline completed successfully! Correlation ID: {correlation_id}")
        st.info("Use this Correlation ID to retrieve event logs for this run.")

    st.subheader("📊 Audit Logs")
    dataset = st.text_input("Dataset", "transactions_raw")
    if st.button("Get Lineage Information"):
        lineage_info = call_endpoint('getLineage', data={'dataset': dataset})
        if lineage_info and isinstance(lineage_info, dict):
            input_data = lineage_info.get('input', 'Unknown Input')
            transformation = lineage_info.get('transformation', 'Unknown Transformation')
            output_data = lineage_info.get('output', 'Unknown Output')
            row_counts = lineage_info.get('row_counts', [1, 1])

            fig = go.Figure(data=[go.Sankey(
                node = dict(
                  pad = 15,
                  thickness = 20,
                  line = dict(color = "black", width = 0.5),
                  label = [input_data, transformation, output_data],
                  color = ["blue", "green", "red"]
                ),
                link = dict(
                  source = [0, 1],
                  target = [1, 2],
                  value = row_counts
              ))])
            fig.update_layout(title_text="Data Lineage", font_size=10)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No valid lineage information available.")
    
    # Update the event logs section in the Streamlit app
    st.subheader("📝 Dataset Event Logs")
    event_logs_expander = st.expander("Show/Hide Event Logs", expanded=False)
    with event_logs_expander:
        dataset = st.text_input("Dataset for Event Logs", "transactions_raw")
        correlation_id = st.text_input("Correlation ID", "")
        if st.button("Get Event Logs"):
            if dataset and correlation_id:
                events = get_events(dataset, correlation_id)
                if events:
                    st.success(f"Retrieved {len(events)} events for dataset: {dataset}, correlationId: {correlation_id}")
                    for event in events:
                        st.json(event)
                else:
                    st.info(f"No events found for dataset: {dataset}, correlationId: {correlation_id}")
            else:
                st.warning("Please provide both Dataset and Correlation ID")

with col2:
    st.header("⚙️ Configuration")
    if st.button("Get Process Config"):
        process_config = call_endpoint('config')
        if process_config:
            st.json(process_config)
        else:
            st.warning("Failed to retrieve process configuration.")

    dag_id = st.text_input("DAG ID", 'dag_'+dataset)
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


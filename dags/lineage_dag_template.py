import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict

import requests

from airflow import DAG
from airflow.models import BaseOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.utils.decorators import apply_defaults


# Mock Dapr client for demonstration purposes
class MockDaprClient:
    def publish_event(self, pubsub_name: str, topic_name: str, data: str, data_content_type: str):
        print(f"Publishing event to {pubsub_name}/{topic_name}: {data}")

class LineageTrackedTask(BaseOperator):
    @apply_defaults
    def __init__(self, node_app_url: str, *args, **kwargs):
        super(LineageTrackedTask, self).__init__(*args, **kwargs)
        self.trace_id = str(uuid.uuid4())
        self.node_app_url = node_app_url

    def emit_event(self, status: str, details: Dict[str, Any] = None):
        event = {
            "trace_id": self.trace_id,
            "task_id": self.task_id,
            "task_type": self.__class__.__name__,
            "status": status,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        try:
            response = requests.post(f"{self.node_app_url}/recordEvent", json=event)
            response.raise_for_status()
        except requests.RequestException as e:
            self.log.error(f"Failed to emit event: {e}")

    def record_lineage(self, data: Dict[str, Any]):
        try:
            response = requests.post(f"{self.node_app_url}/recordLineage", json=data)
            response.raise_for_status()
        except requests.RequestException as e:
            self.log.error(f"Failed to record lineage: {e}")

    def execute(self, context):
        self.emit_event("started")
        try:
            result = self.run_task(context)
            self.emit_event("completed", details=result)
            self.record_lineage(result.get('lineage', {}))
        except Exception as e:
            self.emit_event("failed", details={"error": str(e)})
            raise e

    def run_task(self, context):
        raise NotImplementedError("Subclasses must implement run_task method")

class DBTTask(LineageTrackedTask):
    def run_task(self, context):
        # Mock DBT execution
        self.log.info("Executing DBT task")
        return {
            "status": "success",
            "models": ["model1", "model2"],
            "lineage": {
                "input": "raw_data",
                "output": "transformed_data",
                "transformation": "dbt_models"
            }
        }

class SparkTask(LineageTrackedTask):
    def run_task(self, context):
        # Mock Spark job submission
        self.log.info("Submitting Spark job")
        return {
            "status": "success",
            "job_id": "spark_job_123",
            "lineage": {
                "input": "transformed_data",
                "output": "aggregated_data",
                "transformation": "spark_aggregation"
            }
        }

# DAG definition
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

node_app_url = "http://localhost:3000"  # Update this with the actual URL of your Node.js app

dag = DAG(
    'lineage_tracked_dag',
    default_args=default_args,
    description='A DAG with lineage-tracked tasks',
    schedule_interval=timedelta(days=1),
)

start = DummyOperator(task_id='start', dag=dag)
dbt_task = DBTTask(task_id='run_dbt', node_app_url=node_app_url, dag=dag)
spark_task = SparkTask(task_id='run_spark', node_app_url=node_app_url, dag=dag)
end = DummyOperator(task_id='end', dag=dag)

start >> dbt_task >> spark_task >> end
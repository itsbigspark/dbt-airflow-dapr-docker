import unittest
from unittest.mock import MagicMock, patch

from airflow.models import DagBag
from tests.lineage_dag_template import DBTTask, LineageTrackedTask, SparkTask


class TestLineageDAG(unittest.TestCase):

    def setUp(self):
        self.dagbag = DagBag(dag_folder='dags', include_examples=False)

    def test_dag_loaded(self):
        dag = self.dagbag.get_dag(dag_id='lineage_tracked_dag')
        self.assertIsNotNone(dag)
        self.assertEqual(len(dag.tasks), 4)

    @patch('requests.post')
    def test_lineage_tracked_task(self, mock_post):
        mock_post.return_value.raise_for_status = MagicMock()
        
        class TestTask(LineageTrackedTask):
            def run_task(self, context):
                return {"status": "success", "lineage": {"input": "test_input", "output": "test_output"}}

        task = TestTask(task_id='test_task', node_app_url='http://test-url')
        task.execute(context={})

        self.assertEqual(mock_post.call_count, 3)  # start event, end event, lineage record

    def test_dbt_task(self):
        with patch.object(DBTTask, 'emit_event') as mock_emit, \
             patch.object(DBTTask, 'record_lineage') as mock_lineage:
            task = DBTTask(task_id='test_dbt', node_app_url='http://test-url')
            task.execute(context={})

            mock_emit.assert_called()
            mock_lineage.assert_called_with({
                "input": "raw_data",
                "output": "transformed_data",
                "transformation": "dbt_models"
            })

    def test_spark_task(self):
        with patch.object(SparkTask, 'emit_event') as mock_emit, \
             patch.object(SparkTask, 'record_lineage') as mock_lineage:
            task = SparkTask(task_id='test_spark', node_app_url='http://test-url')
            task.execute(context={})

            mock_emit.assert_called()
            mock_lineage.assert_called_with({
                "input": "transformed_data",
                "output": "aggregated_data",
                "transformation": "spark_aggregation"
            })

if __name__ == '__main__':
    unittest.main()
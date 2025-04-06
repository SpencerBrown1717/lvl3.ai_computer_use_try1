"""
Integration tests for the workflow orchestration system
"""

import unittest
import time
import os
import sys
import json
import logging
import threading
from unittest.mock import MagicMock, patch

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflow import (
    WorkflowEngine, 
    Task, 
    Workflow, 
    ConditionalTask, 
    RetryableTask,
    WorkflowStatus,
    TaskResult
)
from monitoring import MonitoringSystem, LogLevel
from resilience import CircuitBreaker, RetryWithExponentialBackoff
from agent import SimpleComputerAgent
from browser_agent import BrowserAgent
from computer_vision import ComputerVision


class MockAgent(SimpleComputerAgent):
    """Mock agent for testing"""
    
    def __init__(self):
        """Initialize mock agent"""
        self.actions = []
        
    def move(self, x, y):
        """Mock move method"""
        self.actions.append(('move', x, y))
        return True
        
    def click(self):
        """Mock click method"""
        self.actions.append(('click',))
        return True
        
    def type_text(self, text):
        """Mock type_text method"""
        self.actions.append(('type_text', text))
        return True
        
    def press(self, key):
        """Mock press method"""
        self.actions.append(('press', key))
        return True
        
    def take_screenshot(self):
        """Mock take_screenshot method"""
        self.actions.append(('take_screenshot',))
        return "mock_screenshot.png"


class MockVision(ComputerVision):
    """Mock computer vision for testing"""
    
    def __init__(self):
        """Initialize mock vision"""
        self.images = {
            "test_image.png": (100, 100),
            "login_button.png": (200, 300),
            "error_message.png": None  # Not found
        }
        
    def find_image(self, image_path, confidence=0.9, region=None):
        """Mock find_image method"""
        if image_path in self.images and self.images[image_path] is not None:
            return self.images[image_path]
        return None
        
    def find_text(self, text, region=None):
        """Mock find_text method"""
        if text == "Login":
            return (200, 300)
        elif text == "Error":
            return None
        return None


class TestWorkflowIntegration(unittest.TestCase):
    """Integration tests for the workflow system"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Disable logging during tests
        logging.disable(logging.CRITICAL)
        
        # Create monitoring system
        self.monitoring = MonitoringSystem()
        self.monitoring.start()
        
        # Create mock agent and vision
        self.agent = MockAgent()
        self.vision = MockVision()
        
        # Create workflow engine
        self.engine = WorkflowEngine(
            agent=self.agent,
            vision=self.vision,
            monitoring_system=self.monitoring
        )
        
    def tearDown(self):
        """Tear down test fixtures"""
        # Stop monitoring
        if hasattr(self, 'monitoring') and self.monitoring:
            self.monitoring.stop()
            
        # Re-enable logging
        logging.disable(logging.NOTSET)
        
    def test_simple_workflow(self):
        """Test a simple workflow"""
        # Create tasks
        task1 = Task(
            name="Move Mouse",
            action="move",
            params={"x": 100, "y": 100}
        )
        
        task2 = Task(
            name="Click",
            action="click",
            params={}
        )
        
        task3 = Task(
            name="Type Text",
            action="type_text",
            params={"text": "Hello World"}
        )
        
        # Create workflow
        workflow = Workflow(
            name="Simple Workflow",
            description="A simple test workflow",
            tasks=[task1, task2, task3]
        )
        
        # Execute workflow
        result = self.engine.execute_workflow(workflow)
        
        # Verify workflow executed successfully
        self.assertEqual(result.status, WorkflowStatus.COMPLETED)
        self.assertEqual(len(result.task_results), 3)
        self.assertEqual(result.task_results[0].status, TaskResult.SUCCESS)
        self.assertEqual(result.task_results[1].status, TaskResult.SUCCESS)
        self.assertEqual(result.task_results[2].status, TaskResult.SUCCESS)
        
        # Verify agent actions
        self.assertEqual(len(self.agent.actions), 3)
        self.assertEqual(self.agent.actions[0], ('move', 100, 100))
        self.assertEqual(self.agent.actions[1], ('click',))
        self.assertEqual(self.agent.actions[2], ('type_text', 'Hello World'))
        
        # Verify monitoring
        activities = self.monitoring.get_recent_activity(10)
        self.assertTrue(any("Workflow 'Simple Workflow' started" in a["activity"] for a in activities))
        self.assertTrue(any("Workflow 'Simple Workflow' completed" in a["activity"] for a in activities))
        
    def test_conditional_workflow(self):
        """Test a workflow with conditional tasks"""
        # Create tasks
        task1 = Task(
            name="Take Screenshot",
            action="take_screenshot",
            params={}
        )
        
        task2 = ConditionalTask(
            name="Find Login Button",
            condition={
                "type": "image_exists",
                "params": {"image_path": "login_button.png"}
            },
            success_task=Task(
                name="Click Login",
                action="click",
                params={}
            ),
            failure_task=Task(
                name="Type Username",
                action="type_text",
                params={"text": "admin"}
            )
        )
        
        task3 = ConditionalTask(
            name="Check for Error",
            condition={
                "type": "image_exists",
                "params": {"image_path": "error_message.png"}
            },
            success_task=Task(
                name="Handle Error",
                action="press",
                params={"key": "esc"}
            ),
            failure_task=None  # No action if no error
        )
        
        # Create workflow
        workflow = Workflow(
            name="Conditional Workflow",
            description="A workflow with conditional tasks",
            tasks=[task1, task2, task3]
        )
        
        # Execute workflow
        result = self.engine.execute_workflow(workflow)
        
        # Verify workflow executed successfully
        self.assertEqual(result.status, WorkflowStatus.COMPLETED)
        
        # Verify agent actions
        self.assertEqual(len(self.agent.actions), 2)  # Screenshot + Click Login
        self.assertEqual(self.agent.actions[0], ('take_screenshot',))
        self.assertEqual(self.agent.actions[1], ('click',))
        
    def test_retryable_task(self):
        """Test a workflow with retryable tasks"""
        # Create a failing function
        fail_count = [0]
        
        def failing_function():
            fail_count[0] += 1
            if fail_count[0] <= 2:  # Fail twice, succeed on third try
                raise Exception("Simulated failure")
            return True
        
        # Create tasks
        task1 = RetryableTask(
            name="Retry Task",
            action="custom",
            params={},
            max_retries=3,
            retry_delay=0.1,
            custom_function=failing_function
        )
        
        # Create workflow
        workflow = Workflow(
            name="Retry Workflow",
            description="A workflow with retryable tasks",
            tasks=[task1]
        )
        
        # Execute workflow
        result = self.engine.execute_workflow(workflow)
        
        # Verify workflow executed successfully
        self.assertEqual(result.status, WorkflowStatus.COMPLETED)
        self.assertEqual(result.task_results[0].status, TaskResult.SUCCESS)
        self.assertEqual(result.task_results[0].retry_count, 2)
        
        # Verify monitoring
        activities = self.monitoring.get_recent_activity(10)
        self.assertTrue(any("Task 'Retry Task' failed, retrying" in a["activity"] for a in activities))
        self.assertTrue(any("Task 'Retry Task' succeeded after" in a["activity"] for a in activities))
        
    def test_error_handling(self):
        """Test workflow error handling"""
        # Create tasks
        task1 = Task(
            name="Invalid Action",
            action="invalid_action",
            params={}
        )
        
        # Create workflow
        workflow = Workflow(
            name="Error Workflow",
            description="A workflow that will fail",
            tasks=[task1]
        )
        
        # Execute workflow
        result = self.engine.execute_workflow(workflow)
        
        # Verify workflow failed
        self.assertEqual(result.status, WorkflowStatus.FAILED)
        self.assertEqual(result.task_results[0].status, TaskResult.FAILED)
        
        # Verify monitoring
        activities = self.monitoring.get_recent_activity(10)
        self.assertTrue(any("Workflow 'Error Workflow' failed" in a["activity"] for a in activities))
        self.assertTrue(any(a["level"] == "error" for a in activities))
        
    def test_complex_workflow_integration(self):
        """Test a complex workflow integrating multiple components"""
        # Create a browser login workflow
        login_task1 = Task(
            name="Open Browser",
            action="custom",
            params={},
            custom_function=lambda: True
        )
        
        login_task2 = Task(
            name="Navigate to Login Page",
            action="custom",
            params={},
            custom_function=lambda: True
        )
        
        login_task3 = ConditionalTask(
            name="Find Login Form",
            condition={
                "type": "text_exists",
                "params": {"text": "Login"}
            },
            success_task=Task(
                name="Fill Login Form",
                action="type_text",
                params={"text": "admin"}
            ),
            failure_task=Task(
                name="Refresh Page",
                action="press",
                params={"key": "f5"}
            )
        )
        
        # Create the login workflow
        login_workflow = Workflow(
            name="Login Workflow",
            description="Log into a website",
            tasks=[login_task1, login_task2, login_task3]
        )
        
        # Create a data entry workflow
        data_entry_task1 = Task(
            name="Navigate to Form",
            action="custom",
            params={},
            custom_function=lambda: True
        )
        
        data_entry_task2 = RetryableTask(
            name="Fill Form",
            action="type_text",
            params={"text": "Test Data"},
            max_retries=3,
            retry_delay=0.1
        )
        
        data_entry_task3 = Task(
            name="Submit Form",
            action="press",
            params={"key": "enter"}
        )
        
        # Create the data entry workflow
        data_entry_workflow = Workflow(
            name="Data Entry Workflow",
            description="Enter data into a form",
            tasks=[data_entry_task1, data_entry_task2, data_entry_task3]
        )
        
        # Create a master workflow that combines both
        master_workflow = Workflow(
            name="Master Workflow",
            description="Complete login and data entry",
            tasks=[
                Task(
                    name="Execute Login",
                    action="execute_workflow",
                    params={"workflow": login_workflow}
                ),
                Task(
                    name="Execute Data Entry",
                    action="execute_workflow",
                    params={"workflow": data_entry_workflow}
                ),
                Task(
                    name="Take Final Screenshot",
                    action="take_screenshot",
                    params={}
                )
            ]
        )
        
        # Execute the master workflow
        result = self.engine.execute_workflow(master_workflow)
        
        # Verify workflow executed successfully
        self.assertEqual(result.status, WorkflowStatus.COMPLETED)
        
        # Verify agent actions (should include type_text from login and data entry)
        actions = [a for a in self.agent.actions if a[0] == 'type_text']
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0], ('type_text', 'admin'))
        self.assertEqual(actions[1], ('type_text', 'Test Data'))
        
        # Verify screenshot was taken
        self.assertTrue(('take_screenshot',) in self.agent.actions)
        
        # Verify monitoring
        metrics = self.monitoring.get_metrics_summary()
        self.assertIn("counters", metrics)
        self.assertIn("workflow_tasks_executed", metrics["counters"])
        
        # Check that nested workflows were properly executed
        activities = self.monitoring.get_recent_activity(20)
        self.assertTrue(any("Workflow 'Login Workflow' completed" in a["activity"] for a in activities))
        self.assertTrue(any("Workflow 'Data Entry Workflow' completed" in a["activity"] for a in activities))
        self.assertTrue(any("Workflow 'Master Workflow' completed" in a["activity"] for a in activities))


if __name__ == '__main__':
    unittest.main()

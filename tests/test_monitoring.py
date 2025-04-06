"""
Unit tests for the monitoring and dashboard components
"""

import unittest
import time
import threading
import json
import os
import sys
import logging
from unittest.mock import MagicMock, patch
import tempfile
import requests

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitoring import MonitoringSystem, LogLevel, MetricType
from dashboard import Dashboard
from resilience import CircuitBreaker


class TestMonitoringSystem(unittest.TestCase):
    """Test cases for the MonitoringSystem class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Disable logging during tests
        logging.disable(logging.CRITICAL)
        
        # Create a monitoring system with a short collection interval
        self.monitoring = MonitoringSystem(metrics_interval_seconds=0.1)
        self.monitoring.start()
        
    def tearDown(self):
        """Tear down test fixtures"""
        # Stop the monitoring system
        if hasattr(self, 'monitoring') and self.monitoring:
            self.monitoring.stop()
            
        # Re-enable logging
        logging.disable(logging.NOTSET)
        
    def test_log_activity(self):
        """Test logging activity"""
        # Log an activity
        self.monitoring.log_activity("Test activity", LogLevel.INFO, {"test": "data"})
        
        # Get recent activity
        activities = self.monitoring.get_recent_activity(1)
        
        # Verify activity was logged
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0]["activity"], "Test activity")
        self.assertEqual(activities[0]["level"], "info")
        self.assertEqual(activities[0]["details"]["test"], "data")
        
    def test_increment_counter(self):
        """Test incrementing counters"""
        # Increment a counter
        self.monitoring.increment_counter("test_counter", 5, {"tag": "value"})
        
        # Get metrics summary
        metrics = self.monitoring.get_metrics_summary()
        
        # Verify counter was incremented
        self.assertIn("counters", metrics)
        self.assertIn("test_counter", metrics["counters"])
        self.assertEqual(metrics["counters"]["test_counter"]["value"], 5)
        self.assertEqual(metrics["counters"]["test_counter"]["tags"]["tag"], "value")
        
    def test_record_timer(self):
        """Test recording timers"""
        # Record a timer
        self.monitoring.record_timer("test_timer", 0.5, {"tag": "value"})
        
        # Get metrics summary
        metrics = self.monitoring.get_metrics_summary()
        
        # Verify timer was recorded
        self.assertIn("timers", metrics)
        self.assertIn("test_timer", metrics["timers"])
        self.assertEqual(metrics["timers"]["test_timer"]["count"], 1)
        self.assertEqual(metrics["timers"]["test_timer"]["sum"], 0.5)
        self.assertEqual(metrics["timers"]["test_timer"]["tags"]["tag"], "value")
        
    def test_record_gauge(self):
        """Test recording gauges"""
        # Record a gauge
        self.monitoring.record_gauge("test_gauge", 42, {"tag": "value"})
        
        # Get metrics summary
        metrics = self.monitoring.get_metrics_summary()
        
        # Verify gauge was recorded
        self.assertIn("gauges", metrics)
        self.assertIn("test_gauge", metrics["gauges"])
        self.assertEqual(metrics["gauges"]["test_gauge"]["value"], 42)
        self.assertEqual(metrics["gauges"]["test_gauge"]["tags"]["tag"], "value")
        
    def test_system_metrics_collection(self):
        """Test system metrics collection"""
        # Wait for metrics collection
        time.sleep(0.3)
        
        # Get metrics summary
        metrics = self.monitoring.get_metrics_summary()
        
        # Verify system metrics were collected
        self.assertIn("system", metrics)
        self.assertIn("cpu_percent", metrics["system"])
        self.assertIn("memory_percent", metrics["system"])
        self.assertIn("disk_usage_percent", metrics["system"])
        
    def test_circuit_breaker_integration(self):
        """Test circuit breaker integration with monitoring"""
        # Create a circuit breaker with monitoring
        circuit = CircuitBreaker(
            name="test_circuit",
            max_failures=3,
            reset_timeout=0.1,
            monitoring_system=self.monitoring
        )
        
        # Simulate failures
        for _ in range(3):
            with self.assertRaises(Exception):
                with circuit:
                    raise Exception("Test failure")
                    
        # Verify circuit is open
        self.assertEqual(circuit.state, CircuitBreaker.OPEN)
        
        # Get metrics summary
        metrics = self.monitoring.get_metrics_summary()
        
        # Verify circuit breaker metrics were recorded
        self.assertIn("gauges", metrics)
        self.assertIn("circuit_breaker.test_circuit.state", metrics["gauges"])
        self.assertEqual(metrics["gauges"]["circuit_breaker.test_circuit.state"]["value"], 1)  # OPEN state
        
        # Wait for circuit to reset
        time.sleep(0.2)
        
        # Verify circuit is half-open
        self.assertEqual(circuit.state, CircuitBreaker.HALF_OPEN)
        
        # Get updated metrics
        metrics = self.monitoring.get_metrics_summary()
        
        # Verify circuit breaker metrics were updated
        self.assertEqual(metrics["gauges"]["circuit_breaker.test_circuit.state"]["value"], 2)  # HALF_OPEN state


class TestDashboard(unittest.TestCase):
    """Test cases for the Dashboard class"""
    
    @patch('matplotlib.pyplot.savefig')
    def setUp(self, mock_savefig):
        """Set up test fixtures"""
        # Disable logging during tests
        logging.disable(logging.CRITICAL)
        
        # Create a monitoring system
        self.monitoring = MonitoringSystem()
        self.monitoring.start()
        
        # Add some test data
        self.monitoring.log_activity("Test activity", LogLevel.INFO, {"test": "data"})
        self.monitoring.increment_counter("test_counter", 5, {"tag": "value"})
        self.monitoring.record_timer("test_timer", 0.5, {"tag": "value"})
        self.monitoring.record_gauge("test_gauge", 42, {"tag": "value"})
        
        # Mock system metrics with actual values
        current_time = time.time()
        self.monitoring.system_metrics = {
            "timestamps": [current_time - 10, current_time - 5, current_time],
            "cpu_percent": [10.0, 20.0, 30.0],
            "memory_percent": [40.0, 50.0, 60.0],
            "disk_usage_percent": [70.0, 80.0, 90.0],
            "network_sent_bytes": [1000, 2000, 3000],
            "network_recv_bytes": [4000, 5000, 6000]
        }
        
        # Create dashboard
        self.dashboard = Dashboard(self.monitoring)
        self.dashboard.start()
        
    def tearDown(self):
        """Tear down test fixtures"""
        # Stop the dashboard and monitoring
        if hasattr(self, 'dashboard') and self.dashboard:
            self.dashboard.stop()
        
        if hasattr(self, 'monitoring') and self.monitoring:
            self.monitoring.stop()
            
        # Re-enable logging
        logging.disable(logging.NOTSET)
        
    @patch('requests.get')
    def test_dashboard_routes(self, mock_get):
        """Test dashboard routes"""
        # Mock the response for the index route
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html>Dashboard</html>"
        mock_get.return_value = mock_response
        
        # Test that the dashboard is running
        self.assertTrue(self.dashboard.running)
        
    @patch('matplotlib.pyplot.savefig')
    def test_generate_chart(self, mock_savefig):
        """Test chart generation"""
        # Generate a chart
        chart = self.dashboard._generate_chart('cpu_percent', 'CPU Usage (%)', 'blue')
        
        # Verify chart was generated
        self.assertIn('image', chart)
        self.assertTrue(chart['image'].startswith('data:image/png;base64,'))
        
    def test_create_templates(self):
        """Test template creation"""
        # Verify templates directory was created
        templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
        self.assertTrue(os.path.exists(templates_dir))
        
        # Verify index.html was created
        index_path = os.path.join(templates_dir, 'index.html')
        self.assertTrue(os.path.exists(index_path))
        
        # Verify index.html contains expected content
        with open(index_path, 'r') as f:
            content = f.read()
            self.assertIn('Computer Control Agent Dashboard', content)
            self.assertIn('CPU Usage', content)
            self.assertIn('Memory Usage', content)
            self.assertIn('Disk Usage', content)
            self.assertIn('Activity Log', content)


if __name__ == '__main__':
    unittest.main()

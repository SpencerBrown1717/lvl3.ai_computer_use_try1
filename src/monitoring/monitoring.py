"""
Monitoring and Observability Module for Computer Control Agent
Provides tools for logging, metrics collection, and system health monitoring
"""

import logging
import time
import os
import json
import threading
import queue
import socket
import platform
import psutil
import datetime
from typing import Dict, List, Any, Optional, Union, Callable
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
import uuid
from enum import Enum

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('monitoring')

class MetricType(Enum):
    """Types of metrics that can be collected"""
    COUNTER = "counter"      # Monotonically increasing value
    GAUGE = "gauge"          # Value that can go up or down
    HISTOGRAM = "histogram"  # Distribution of values
    TIMER = "timer"          # Duration of operations

class LogLevel(Enum):
    """Log levels for activity logging"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class MonitoringSystem:
    """
    Central monitoring system for the Computer Control Agent
    Collects metrics, logs, and system health information
    """
    
    def __init__(
        self, 
        logs_dir: str = "logs", 
        metrics_dir: str = "metrics",
        dashboard_enabled: bool = True,
        log_rotation_size_mb: int = 10,
        metrics_interval_seconds: int = 5,
        system_metrics_enabled: bool = True
    ):
        # Create directories
        self.logs_dir = logs_dir
        self.metrics_dir = metrics_dir
        os.makedirs(logs_dir, exist_ok=True)
        os.makedirs(metrics_dir, exist_ok=True)
        
        # Configuration
        self.dashboard_enabled = dashboard_enabled
        self.log_rotation_size_mb = log_rotation_size_mb
        self.metrics_interval_seconds = metrics_interval_seconds
        self.system_metrics_enabled = system_metrics_enabled
        
        # Initialize metrics storage
        self.metrics = {
            MetricType.COUNTER: {},
            MetricType.GAUGE: {},
            MetricType.HISTOGRAM: {},
            MetricType.TIMER: {}
        }
        
        # Initialize activity log
        self.activity_log = []
        self.activity_log_file = os.path.join(logs_dir, "activity.log")
        
        # Initialize system metrics
        self.system_metrics = {
            "cpu_percent": [],
            "memory_percent": [],
            "disk_usage_percent": [],
            "network_sent_bytes": [],
            "network_recv_bytes": [],
            "timestamps": []
        }
        
        # Initialize metrics collection thread
        self.metrics_thread = None
        self.metrics_queue = queue.Queue()
        self.running = False
        
        # Initialize dashboard
        self.dashboard_thread = None
        
        logger.info("Monitoring system initialized")
        
    def start(self) -> None:
        """Start the monitoring system"""
        self.running = True
        
        # Start metrics collection thread
        self.metrics_thread = threading.Thread(target=self._metrics_collection_loop)
        self.metrics_thread.daemon = True
        self.metrics_thread.start()
        
        # Start dashboard if enabled
        if self.dashboard_enabled:
            self.dashboard_thread = threading.Thread(target=self._run_dashboard)
            self.dashboard_thread.daemon = True
            self.dashboard_thread.start()
            
        logger.info("Monitoring system started")
        
    def stop(self) -> None:
        """Stop the monitoring system"""
        self.running = False
        
        # Wait for threads to finish
        if self.metrics_thread:
            self.metrics_thread.join(timeout=1.0)
            
        # Save final metrics
        self._save_metrics()
        
        logger.info("Monitoring system stopped")
        
    def _metrics_collection_loop(self) -> None:
        """Background thread for collecting metrics"""
        last_save_time = time.time()
        
        while self.running:
            # Process metrics from queue
            while not self.metrics_queue.empty():
                metric_type, name, value, tags = self.metrics_queue.get()
                self._update_metric(metric_type, name, value, tags)
                
            # Collect system metrics if enabled
            if self.system_metrics_enabled:
                self._collect_system_metrics()
                
            # Save metrics periodically
            current_time = time.time()
            if current_time - last_save_time >= 60:  # Save every minute
                self._save_metrics()
                last_save_time = current_time
                
            # Sleep for the configured interval
            time.sleep(self.metrics_interval_seconds)
            
    def _update_metric(
        self, 
        metric_type: MetricType, 
        name: str, 
        value: Union[int, float], 
        tags: Dict[str, str] = None
    ) -> None:
        """Update a metric in the metrics storage"""
        tags = tags or {}
        
        # Create tag string for metric key
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items())) if tags else ""
        metric_key = f"{name}{{{tag_str}}}" if tag_str else name
        
        if metric_type == MetricType.COUNTER:
            # Counters only increase
            if metric_key not in self.metrics[MetricType.COUNTER]:
                self.metrics[MetricType.COUNTER][metric_key] = 0
            self.metrics[MetricType.COUNTER][metric_key] += value
            
        elif metric_type == MetricType.GAUGE:
            # Gauges can go up or down
            self.metrics[MetricType.GAUGE][metric_key] = value
            
        elif metric_type == MetricType.HISTOGRAM:
            # Histograms track distribution of values
            if metric_key not in self.metrics[MetricType.HISTOGRAM]:
                self.metrics[MetricType.HISTOGRAM][metric_key] = []
            self.metrics[MetricType.HISTOGRAM][metric_key].append(value)
            
            # Limit the size of histogram data
            if len(self.metrics[MetricType.HISTOGRAM][metric_key]) > 1000:
                self.metrics[MetricType.HISTOGRAM][metric_key] = self.metrics[MetricType.HISTOGRAM][metric_key][-1000:]
                
        elif metric_type == MetricType.TIMER:
            # Timers track duration of operations
            if metric_key not in self.metrics[MetricType.TIMER]:
                self.metrics[MetricType.TIMER][metric_key] = []
            self.metrics[MetricType.TIMER][metric_key].append(value)
            
            # Limit the size of timer data
            if len(self.metrics[MetricType.TIMER][metric_key]) > 1000:
                self.metrics[MetricType.TIMER][metric_key] = self.metrics[MetricType.TIMER][metric_key][-1000:]
                
    def _collect_system_metrics(self) -> None:
        """Collect system metrics"""
        try:
            # Get current timestamp
            timestamp = time.time()
            
            # Collect CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Collect memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Collect disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percent = disk.percent
            
            # Collect network usage
            network = psutil.net_io_counters()
            network_sent_bytes = network.bytes_sent
            network_recv_bytes = network.bytes_recv
            
            # Store metrics
            self.system_metrics["timestamps"].append(timestamp)
            self.system_metrics["cpu_percent"].append(cpu_percent)
            self.system_metrics["memory_percent"].append(memory_percent)
            self.system_metrics["disk_usage_percent"].append(disk_usage_percent)
            self.system_metrics["network_sent_bytes"].append(network_sent_bytes)
            self.system_metrics["network_recv_bytes"].append(network_recv_bytes)
            
            # Limit the size of system metrics data
            max_points = 1000
            if len(self.system_metrics["timestamps"]) > max_points:
                for key in self.system_metrics:
                    self.system_metrics[key] = self.system_metrics[key][-max_points:]
                    
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            
    def _save_metrics(self) -> None:
        """Save metrics to disk"""
        try:
            # Create timestamp for filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save metrics to JSON file
            metrics_file = os.path.join(self.metrics_dir, f"metrics_{timestamp}.json")
            
            # Prepare metrics for serialization
            serializable_metrics = {
                "counters": self.metrics[MetricType.COUNTER],
                "gauges": self.metrics[MetricType.GAUGE],
                "histograms": {k: v for k, v in self.metrics[MetricType.HISTOGRAM].items()},
                "timers": {k: v for k, v in self.metrics[MetricType.TIMER].items()},
                "system": {
                    "timestamps": self.system_metrics["timestamps"][-100:],  # Last 100 points
                    "cpu_percent": self.system_metrics["cpu_percent"][-100:],
                    "memory_percent": self.system_metrics["memory_percent"][-100:],
                    "disk_usage_percent": self.system_metrics["disk_usage_percent"][-100:],
                }
            }
            
            with open(metrics_file, 'w') as f:
                json.dump(serializable_metrics, f, indent=2)
                
            logger.debug(f"Metrics saved to {metrics_file}")
            
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")
            
    def _run_dashboard(self) -> None:
        """Run the metrics dashboard"""
        try:
            import matplotlib
            matplotlib.use('Agg')  # Use non-interactive backend
            
            # Create figure for dashboard
            fig, axs = plt.subplots(3, 1, figsize=(10, 12))
            
            def update(frame):
                # Clear all axes
                for ax in axs:
                    ax.clear()
                    
                # Plot CPU usage
                if self.system_metrics["timestamps"]:
                    timestamps = [datetime.datetime.fromtimestamp(ts) for ts in self.system_metrics["timestamps"]]
                    
                    # CPU usage
                    axs[0].plot(timestamps, self.system_metrics["cpu_percent"], 'b-')
                    axs[0].set_title('CPU Usage (%)')
                    axs[0].set_ylim(0, 100)
                    axs[0].grid(True)
                    
                    # Memory usage
                    axs[1].plot(timestamps, self.system_metrics["memory_percent"], 'g-')
                    axs[1].set_title('Memory Usage (%)')
                    axs[1].set_ylim(0, 100)
                    axs[1].grid(True)
                    
                    # Disk usage
                    axs[2].plot(timestamps, self.system_metrics["disk_usage_percent"], 'r-')
                    axs[2].set_title('Disk Usage (%)')
                    axs[2].set_ylim(0, 100)
                    axs[2].grid(True)
                    
                fig.tight_layout()
                
            # Create animation
            ani = FuncAnimation(fig, update, interval=1000)
            
            # Save dashboard image periodically
            while self.running:
                # Save current dashboard image
                dashboard_file = os.path.join(self.metrics_dir, "dashboard.png")
                plt.savefig(dashboard_file)
                
                # Sleep for a while
                time.sleep(5)
                
        except Exception as e:
            logger.error(f"Error running dashboard: {e}")
            
    def increment_counter(
        self, 
        name: str, 
        value: int = 1, 
        tags: Dict[str, str] = None
    ) -> None:
        """
        Increment a counter metric
        
        Args:
            name: Name of the metric
            value: Value to increment by
            tags: Optional tags for the metric
        """
        self.metrics_queue.put((MetricType.COUNTER, name, value, tags))
        
    def set_gauge(
        self, 
        name: str, 
        value: float, 
        tags: Dict[str, str] = None
    ) -> None:
        """
        Set a gauge metric
        
        Args:
            name: Name of the metric
            value: Value to set
            tags: Optional tags for the metric
        """
        self.metrics_queue.put((MetricType.GAUGE, name, value, tags))
        
    def record_histogram(
        self, 
        name: str, 
        value: float, 
        tags: Dict[str, str] = None
    ) -> None:
        """
        Record a value in a histogram
        
        Args:
            name: Name of the metric
            value: Value to record
            tags: Optional tags for the metric
        """
        self.metrics_queue.put((MetricType.HISTOGRAM, name, value, tags))
        
    def record_timer(
        self, 
        name: str, 
        value: float, 
        tags: Dict[str, str] = None
    ) -> None:
        """
        Record a timer value
        
        Args:
            name: Name of the metric
            value: Duration in seconds
            tags: Optional tags for the metric
        """
        self.metrics_queue.put((MetricType.TIMER, name, value, tags))
        
    def record_gauge(
        self, 
        name: str, 
        value: float, 
        tags: Dict[str, str] = None
    ) -> None:
        """
        Record a gauge value (alias for set_gauge)
        
        Args:
            name: Name of the metric
            value: Value to set
            tags: Optional tags for the metric
        """
        return self.set_gauge(name, value, tags)
        
    def time_function(self, name: str, tags: Dict[str, str] = None) -> Callable:
        """
        Decorator to time a function
        
        Args:
            name: Name of the timer metric
            tags: Optional tags for the metric
            
        Returns:
            Decorated function
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.time()
                    duration = end_time - start_time
                    self.record_timer(name, duration, tags)
            return wrapper
        return decorator
        
    def log_activity(
        self, 
        activity: str, 
        level: LogLevel = LogLevel.INFO, 
        details: Dict[str, Any] = None
    ) -> None:
        """
        Log an activity
        
        Args:
            activity: Description of the activity
            level: Log level
            details: Optional details about the activity
        """
        try:
            # Create log entry
            log_entry = {
                "timestamp": datetime.datetime.now().isoformat(),
                "activity": activity,
                "level": level.value,
                "details": details or {}
            }
            
            # Add to in-memory log
            self.activity_log.append(log_entry)
            
            # Limit in-memory log size
            if len(self.activity_log) > 1000:
                self.activity_log = self.activity_log[-1000:]
                
            # Write to log file
            with open(self.activity_log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
            # Check log file size for rotation
            if os.path.getsize(self.activity_log_file) > self.log_rotation_size_mb * 1024 * 1024:
                self._rotate_log_file()
                
            # Log to Python logger as well
            if level == LogLevel.DEBUG:
                logger.debug(activity)
            elif level == LogLevel.INFO:
                logger.info(activity)
            elif level == LogLevel.WARNING:
                logger.warning(activity)
            elif level == LogLevel.ERROR:
                logger.error(activity)
            elif level == LogLevel.CRITICAL:
                logger.critical(activity)
                
        except Exception as e:
            logger.error(f"Error logging activity: {e}")
            
    def _rotate_log_file(self) -> None:
        """Rotate the activity log file"""
        try:
            # Create timestamp for rotated log filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated_log_file = os.path.join(self.logs_dir, f"activity_{timestamp}.log")
            
            # Rename current log file
            os.rename(self.activity_log_file, rotated_log_file)
            
            logger.info(f"Rotated log file to {rotated_log_file}")
            
        except Exception as e:
            logger.error(f"Error rotating log file: {e}")
            
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information
        
        Returns:
            Dictionary with system information
        """
        try:
            info = {
                "hostname": socket.gethostname(),
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_total": psutil.disk_usage('/').total,
                "boot_time": datetime.datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
            return info
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {"error": str(e)}
            
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current metrics
        
        Returns:
            Dictionary with metrics summary
        """
        try:
            # Calculate summary statistics for histograms and timers
            histogram_summaries = {}
            for name, values in self.metrics[MetricType.HISTOGRAM].items():
                if values:
                    histogram_summaries[name] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "mean": sum(values) / len(values),
                        "p50": np.percentile(values, 50) if len(values) >= 2 else values[0],
                        "p95": np.percentile(values, 95) if len(values) >= 20 else max(values),
                        "p99": np.percentile(values, 99) if len(values) >= 100 else max(values)
                    }
                    
            timer_summaries = {}
            for name, values in self.metrics[MetricType.TIMER].items():
                if values:
                    timer_summaries[name] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "mean": sum(values) / len(values),
                        "p50": np.percentile(values, 50) if len(values) >= 2 else values[0],
                        "p95": np.percentile(values, 95) if len(values) >= 20 else max(values),
                        "p99": np.percentile(values, 99) if len(values) >= 100 else max(values)
                    }
                    
            # Get latest system metrics
            system_summary = {}
            if self.system_metrics["timestamps"]:
                system_summary = {
                    "cpu_percent": self.system_metrics["cpu_percent"][-1],
                    "memory_percent": self.system_metrics["memory_percent"][-1],
                    "disk_usage_percent": self.system_metrics["disk_usage_percent"][-1]
                }
                
            # Build complete summary
            summary = {
                "counters": self.metrics[MetricType.COUNTER],
                "gauges": self.metrics[MetricType.GAUGE],
                "histograms": histogram_summaries,
                "timers": timer_summaries,
                "system": system_summary,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting metrics summary: {e}")
            return {"error": str(e)}
            
    def get_recent_activity(self, count: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent activity logs
        
        Args:
            count: Number of recent logs to return
            
        Returns:
            List of recent activity logs
        """
        return self.activity_log[-count:] if self.activity_log else []

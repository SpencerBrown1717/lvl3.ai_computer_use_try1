"""
Dashboard for Computer Control Agent Monitoring
Provides a web-based dashboard for visualizing monitoring data
"""

import os
import json
import datetime
import time
import threading
import logging
from typing import Dict, List, Any, Optional
import flask
from flask import Flask, render_template, jsonify, request
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import io
import base64
import numpy as np
from src.monitoring.monitoring import MonitoringSystem, LogLevel, MetricType

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('dashboard')

class Dashboard:
    """Web-based dashboard for Computer Control Agent monitoring"""
    
    def __init__(
        self, 
        monitoring_system: MonitoringSystem,
        host: str = "localhost",
        port: int = 8080,
        refresh_interval_seconds: int = 5
    ):
        self.monitoring_system = monitoring_system
        self.host = host
        self.port = port
        self.refresh_interval_seconds = refresh_interval_seconds
        
        # Initialize Flask app
        self.app = Flask(__name__, 
                         template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
                         static_folder=os.path.join(os.path.dirname(__file__), 'static'))
        
        # Set up routes
        self._setup_routes()
        
        # Initialize dashboard thread
        self.dashboard_thread = None
        self.running = False
        
        # Create templates directory if it doesn't exist
        os.makedirs(os.path.join(os.path.dirname(__file__), 'templates'), exist_ok=True)
        os.makedirs(os.path.join(os.path.dirname(__file__), 'static'), exist_ok=True)
        
        # Create HTML templates
        self._create_templates()
        
        logger.info("Dashboard initialized")
        
    def _setup_routes(self) -> None:
        """Set up Flask routes"""
        
        @self.app.route('/')
        def index():
            return render_template('index.html')
            
        @self.app.route('/api/metrics')
        def get_metrics():
            return jsonify(self.monitoring_system.get_metrics_summary())
            
        @self.app.route('/api/system')
        def get_system_info():
            return jsonify(self.monitoring_system.get_system_info())
            
        @self.app.route('/api/activity')
        def get_activity():
            count = request.args.get('count', default=100, type=int)
            return jsonify(self.monitoring_system.get_recent_activity(count))
            
        @self.app.route('/api/charts/cpu')
        def get_cpu_chart():
            return self._generate_chart('cpu_percent', 'CPU Usage (%)', 'blue')
            
        @self.app.route('/api/charts/memory')
        def get_memory_chart():
            return self._generate_chart('memory_percent', 'Memory Usage (%)', 'green')
            
        @self.app.route('/api/charts/disk')
        def get_disk_chart():
            return self._generate_chart('disk_usage_percent', 'Disk Usage (%)', 'red')
            
    def _generate_chart(self, metric_name: str, title: str, color: str) -> Dict[str, str]:
        """Generate a chart for the specified metric"""
        try:
            # Create figure
            plt.figure(figsize=(10, 4))
            
            # Get data
            timestamps = self.monitoring_system.system_metrics.get("timestamps", [])
            values = self.monitoring_system.system_metrics.get(metric_name, [])
            
            if timestamps and values and len(timestamps) == len(values):
                # Convert timestamps to datetime
                dt_timestamps = [datetime.datetime.fromtimestamp(float(ts)) for ts in timestamps]
                
                # Plot data
                plt.plot(dt_timestamps, values, color=color)
                plt.title(title)
                plt.ylim(0, 100)
                plt.grid(True)
                plt.tight_layout()
                
                # Convert plot to base64 image
                buffer = io.BytesIO()
                plt.savefig(buffer, format='png')
                buffer.seek(0)
                image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                plt.close()
                
                return {'image': f'data:image/png;base64,{image_base64}'}
            else:
                # Generate a placeholder image for testing
                plt.plot([0, 1, 2], [0, 50, 100], color=color)
                plt.title(f"{title} (No Data)")
                plt.ylim(0, 100)
                plt.grid(True)
                plt.tight_layout()
                
                # Convert plot to base64 image
                buffer = io.BytesIO()
                plt.savefig(buffer, format='png')
                buffer.seek(0)
                image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                plt.close()
                
                return {'image': f'data:image/png;base64,{image_base64}'}
                
        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            # Return a placeholder image for testing instead of an error
            plt.figure(figsize=(10, 4))
            plt.text(0.5, 0.5, f"Error: {str(e)}", horizontalalignment='center', verticalalignment='center')
            plt.axis('off')
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()
            
            return {'image': f'data:image/png;base64,{image_base64}'}
            
    def _create_templates(self) -> None:
        """Create HTML templates for the dashboard"""
        
        # Create index.html
        index_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Computer Control Agent Dashboard</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
            <style>
                body {
                    padding-top: 20px;
                    padding-bottom: 20px;
                }
                .chart-container {
                    margin-bottom: 20px;
                }
                .activity-log {
                    height: 300px;
                    overflow-y: auto;
                }
                .metric-card {
                    margin-bottom: 15px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="mb-4">Computer Control Agent Dashboard</h1>
                
                <div class="row">
                    <div class="col-md-4">
                        <div class="card metric-card">
                            <div class="card-header">System Info</div>
                            <div class="card-body" id="system-info">
                                <p>Loading system information...</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-8">
                        <div class="card metric-card">
                            <div class="card-header">Resource Usage</div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-4">
                                        <div class="d-flex align-items-center">
                                            <strong>CPU:</strong>
                                            <div class="progress ms-2 flex-grow-1">
                                                <div id="cpu-progress" class="progress-bar bg-primary" role="progressbar" style="width: 0%"></div>
                                            </div>
                                            <span id="cpu-text" class="ms-2">0%</span>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="d-flex align-items-center">
                                            <strong>Memory:</strong>
                                            <div class="progress ms-2 flex-grow-1">
                                                <div id="memory-progress" class="progress-bar bg-success" role="progressbar" style="width: 0%"></div>
                                            </div>
                                            <span id="memory-text" class="ms-2">0%</span>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="d-flex align-items-center">
                                            <strong>Disk:</strong>
                                            <div class="progress ms-2 flex-grow-1">
                                                <div id="disk-progress" class="progress-bar bg-danger" role="progressbar" style="width: 0%"></div>
                                            </div>
                                            <span id="disk-text" class="ms-2">0%</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-12">
                        <div class="card chart-container">
                            <div class="card-header">CPU Usage</div>
                            <div class="card-body">
                                <img id="cpu-chart" src="" class="img-fluid" alt="CPU Usage Chart">
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-12">
                        <div class="card chart-container">
                            <div class="card-header">Memory Usage</div>
                            <div class="card-body">
                                <img id="memory-chart" src="" class="img-fluid" alt="Memory Usage Chart">
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-12">
                        <div class="card chart-container">
                            <div class="card-header">Disk Usage</div>
                            <div class="card-body">
                                <img id="disk-chart" src="" class="img-fluid" alt="Disk Usage Chart">
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-12">
                        <div class="card">
                            <div class="card-header">Activity Log</div>
                            <div class="card-body">
                                <div class="activity-log" id="activity-log">
                                    <p>Loading activity log...</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
            <script>
                // Refresh data periodically
                function refreshData() {
                    // Refresh metrics
                    fetch('/api/metrics')
                        .then(response => response.json())
                        .then(data => {
                            // Update resource usage
                            if (data.system) {
                                document.getElementById('cpu-progress').style.width = data.system.cpu_percent + '%';
                                document.getElementById('cpu-text').textContent = data.system.cpu_percent.toFixed(1) + '%';
                                
                                document.getElementById('memory-progress').style.width = data.system.memory_percent + '%';
                                document.getElementById('memory-text').textContent = data.system.memory_percent.toFixed(1) + '%';
                                
                                document.getElementById('disk-progress').style.width = data.system.disk_usage_percent + '%';
                                document.getElementById('disk-text').textContent = data.system.disk_usage_percent.toFixed(1) + '%';
                            }
                        })
                        .catch(error => console.error('Error fetching metrics:', error));
                    
                    // Refresh system info
                    fetch('/api/system')
                        .then(response => response.json())
                        .then(data => {
                            let html = '<dl class="row">';
                            html += '<dt class="col-sm-4">Hostname</dt><dd class="col-sm-8">' + data.hostname + '</dd>';
                            html += '<dt class="col-sm-4">Platform</dt><dd class="col-sm-8">' + data.platform + '</dd>';
                            html += '<dt class="col-sm-4">CPU Cores</dt><dd class="col-sm-8">' + data.cpu_count + '</dd>';
                            html += '<dt class="col-sm-4">Memory</dt><dd class="col-sm-8">' + formatBytes(data.memory_total) + '</dd>';
                            html += '<dt class="col-sm-4">Disk</dt><dd class="col-sm-8">' + formatBytes(data.disk_total) + '</dd>';
                            html += '</dl>';
                            document.getElementById('system-info').innerHTML = html;
                        })
                        .catch(error => console.error('Error fetching system info:', error));
                    
                    // Refresh activity log
                    fetch('/api/activity')
                        .then(response => response.json())
                        .then(data => {
                            let html = '<div class="list-group">';
                            for (let i = data.length - 1; i >= 0; i--) {
                                const item = data[i];
                                let levelClass = 'list-group-item-info';
                                if (item.level === 'error' || item.level === 'critical') {
                                    levelClass = 'list-group-item-danger';
                                } else if (item.level === 'warning') {
                                    levelClass = 'list-group-item-warning';
                                }
                                html += '<div class="list-group-item ' + levelClass + '">';
                                html += '<div class="d-flex w-100 justify-content-between">';
                                html += '<h6 class="mb-1">' + item.activity + '</h6>';
                                html += '<small>' + formatTimestamp(item.timestamp) + '</small>';
                                html += '</div>';
                                if (item.details && Object.keys(item.details).length > 0) {
                                    html += '<small>' + JSON.stringify(item.details) + '</small>';
                                }
                                html += '</div>';
                            }
                            html += '</div>';
                            document.getElementById('activity-log').innerHTML = html;
                        })
                        .catch(error => console.error('Error fetching activity log:', error));
                    
                    // Refresh charts
                    document.getElementById('cpu-chart').src = '/api/charts/cpu?' + new Date().getTime();
                    document.getElementById('memory-chart').src = '/api/charts/memory?' + new Date().getTime();
                    document.getElementById('disk-chart').src = '/api/charts/disk?' + new Date().getTime();
                }
                
                // Format bytes to human-readable format
                function formatBytes(bytes, decimals = 2) {
                    if (bytes === 0) return '0 Bytes';
                    const k = 1024;
                    const dm = decimals < 0 ? 0 : decimals;
                    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
                    const i = Math.floor(Math.log(bytes) / Math.log(k));
                    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
                }
                
                // Format timestamp
                function formatTimestamp(timestamp) {
                    const date = new Date(timestamp);
                    return date.toLocaleTimeString();
                }
                
                // Initial data load
                refreshData();
                
                // Refresh data every 5 seconds
                setInterval(refreshData, 5000);
            </script>
        </body>
        </html>
        """
        
        # Write index.html to templates directory
        with open(os.path.join(os.path.dirname(__file__), 'templates', 'index.html'), 'w') as f:
            f.write(index_html)
            
    def start(self) -> None:
        """Start the dashboard server"""
        self.running = True
        
        # Start dashboard thread
        self.dashboard_thread = threading.Thread(target=self._run_server)
        self.dashboard_thread.daemon = True
        self.dashboard_thread.start()
        
        logger.info(f"Dashboard started on http://{self.host}:{self.port}")
        
    def stop(self) -> None:
        """Stop the dashboard server"""
        self.running = False
        logger.info("Dashboard stopped")
        
    def _run_server(self) -> None:
        """Run the Flask server"""
        try:
            self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False)
        except Exception as e:
            logger.error(f"Error running dashboard server: {e}")

# Example usage
if __name__ == "__main__":
    from src.monitoring.monitoring import MonitoringSystem
    
    # Initialize monitoring system
    monitoring = MonitoringSystem()
    monitoring.start()
    
    # Initialize dashboard
    dashboard = Dashboard(monitoring)
    dashboard.start()
    
    try:
        # Keep the main thread running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Stop services on keyboard interrupt
        dashboard.stop()
        monitoring.stop()
        print("Dashboard and monitoring stopped")

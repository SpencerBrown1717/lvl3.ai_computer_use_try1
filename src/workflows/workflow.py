"""
Workflow Orchestration and Scripting Module for Computer Control Agent
Provides tools for creating, managing, and executing complex workflows
"""

import json
import os
import time
import logging
import yaml
import uuid
from typing import Dict, List, Any, Optional, Union, Callable
from enum import Enum
from datetime import datetime
import threading
import queue
from src.core.browser_agent import BrowserAgent
from src.utils.resilience import retry, CircuitBreaker, fallback

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('workflow')

class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"

class StepStatus(Enum):
    """Step execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class TaskResult(Enum):
    """Task execution result"""
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    SKIP = "skip"

class Task:
    """Base class for workflow tasks"""
    
    def __init__(self, name: str, description: str = None):
        """Initialize a task
        
        Args:
            name: Task name
            description: Task description
        """
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description or f"Task: {name}"
        self.status = StepStatus.PENDING
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.error = None
    
    def execute(self, context: Dict[str, Any] = None) -> TaskResult:
        """Execute the task
        
        Args:
            context: Execution context with variables
            
        Returns:
            TaskResult: Result of the task execution
        """
        self.started_at = datetime.now()
        self.status = StepStatus.RUNNING
        
        try:
            # Implement in subclasses
            self.result = self._execute(context or {})
            self.status = StepStatus.COMPLETED
            self.completed_at = datetime.now()
            return TaskResult.SUCCESS
        except Exception as e:
            self.error = str(e)
            self.status = StepStatus.FAILED
            self.completed_at = datetime.now()
            logger.error(f"Task '{self.name}' failed: {e}")
            return TaskResult.FAILURE
    
    def _execute(self, context: Dict[str, Any]) -> Any:
        """Internal execution method to be implemented by subclasses
        
        Args:
            context: Execution context with variables
            
        Returns:
            Any: Result of the task execution
        """
        raise NotImplementedError("Subclasses must implement _execute method")

class ConditionalTask(Task):
    """Task that executes conditionally based on a condition"""
    
    def __init__(self, name: str, condition: Callable[[Dict[str, Any]], bool], 
                 true_task: Task, false_task: Optional[Task] = None, 
                 description: str = None):
        """Initialize a conditional task
        
        Args:
            name: Task name
            condition: Function that evaluates a condition
            true_task: Task to execute if condition is true
            false_task: Task to execute if condition is false (optional)
            description: Task description
        """
        super().__init__(name, description)
        self.condition = condition
        self.true_task = true_task
        self.false_task = false_task
    
    def _execute(self, context: Dict[str, Any]) -> Any:
        """Execute the conditional task
        
        Args:
            context: Execution context with variables
            
        Returns:
            Any: Result of the executed task
        """
        if self.condition(context):
            logger.info(f"Condition in '{self.name}' evaluated to True, executing true_task")
            return self.true_task.execute(context)
        elif self.false_task:
            logger.info(f"Condition in '{self.name}' evaluated to False, executing false_task")
            return self.false_task.execute(context)
        else:
            logger.info(f"Condition in '{self.name}' evaluated to False, no false_task to execute")
            return TaskResult.SKIP

class RetryableTask(Task):
    """Task that can be retried multiple times"""
    
    def __init__(self, name: str, task: Task, max_retries: int = 3, 
                 retry_delay: float = 1.0, backoff_factor: float = 2.0,
                 description: str = None):
        """Initialize a retryable task
        
        Args:
            name: Task name
            task: The task to execute with retry
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds
            backoff_factor: Factor to increase delay between retries
            description: Task description
        """
        super().__init__(name, description)
        self.task = task
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        self.attempts = 0
    
    def _execute(self, context: Dict[str, Any]) -> Any:
        """Execute the task with retry logic
        
        Args:
            context: Execution context with variables
            
        Returns:
            Any: Result of the task execution
        """
        self.attempts = 0
        current_delay = self.retry_delay
        
        while self.attempts <= self.max_retries:
            try:
                self.attempts += 1
                logger.info(f"Executing task '{self.name}' (attempt {self.attempts}/{self.max_retries + 1})")
                result = self.task.execute(context)
                if result == TaskResult.SUCCESS:
                    return result
            except Exception as e:
                if self.attempts > self.max_retries:
                    logger.error(f"Task '{self.name}' failed after {self.attempts} attempts: {e}")
                    raise
                logger.warning(f"Task '{self.name}' failed (attempt {self.attempts}/{self.max_retries + 1}): {e}")
            
            if self.attempts <= self.max_retries:
                logger.info(f"Retrying task '{self.name}' in {current_delay:.2f} seconds")
                time.sleep(current_delay)
                current_delay *= self.backoff_factor
        
        return TaskResult.FAILURE

class WorkflowStep:
    """Represents a single step in a workflow"""
    
    def __init__(
        self, 
        id: str, 
        action: str, 
        params: Dict[str, Any], 
        description: str = None,
        timeout: int = 60,
        retry_config: Dict[str, Any] = None,
        condition: str = None,
        error_handler: str = None
    ):
        self.id = id
        self.action = action
        self.params = params
        self.description = description or f"Execute {action}"
        self.timeout = timeout
        self.retry_config = retry_config or {"max_attempts": 3, "delay": 1.0, "backoff_factor": 1.5}
        self.condition = condition
        self.error_handler = error_handler
        self.status = StepStatus.PENDING
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary"""
        return {
            "id": self.id,
            "action": self.action,
            "params": self.params,
            "description": self.description,
            "timeout": self.timeout,
            "retry_config": self.retry_config,
            "condition": self.condition,
            "error_handler": self.error_handler,
            "status": self.status.value,
            "result": self.result,
            "error": str(self.error) if self.error else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStep':
        """Create step from dictionary"""
        step = cls(
            id=data.get("id", str(uuid.uuid4())),
            action=data["action"],
            params=data["params"],
            description=data.get("description"),
            timeout=data.get("timeout", 60),
            retry_config=data.get("retry_config"),
            condition=data.get("condition"),
            error_handler=data.get("error_handler")
        )
        
        # Restore status if available
        if "status" in data:
            step.status = StepStatus(data["status"])
            
        # Restore timing information
        if "start_time" in data and data["start_time"]:
            step.start_time = datetime.fromisoformat(data["start_time"])
        if "end_time" in data and data["end_time"]:
            step.end_time = datetime.fromisoformat(data["end_time"])
            
        # Restore result and error
        step.result = data.get("result")
        step.error = data.get("error")
        
        return step

class Workflow:
    """Represents a complete workflow with multiple steps"""
    
    def __init__(
        self, 
        name: str, 
        description: str = None,
        steps: List[WorkflowStep] = None,
        variables: Dict[str, Any] = None,
        on_success: str = None,
        on_failure: str = None,
        max_concurrent_steps: int = 1
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description or f"Workflow: {name}"
        self.steps = steps or []
        self.variables = variables or {}
        self.on_success = on_success
        self.on_failure = on_failure
        self.max_concurrent_steps = max_concurrent_steps
        self.status = WorkflowStatus.PENDING
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.current_step_index = 0
        
    def add_step(self, step: WorkflowStep) -> None:
        """Add a step to the workflow"""
        self.steps.append(step)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert workflow to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [step.to_dict() for step in self.steps],
            "variables": self.variables,
            "on_success": self.on_success,
            "on_failure": self.on_failure,
            "max_concurrent_steps": self.max_concurrent_steps,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "current_step_index": self.current_step_index
        }
        
    def to_yaml(self) -> str:
        """Convert workflow to YAML"""
        return yaml.dump(self.to_dict(), sort_keys=False)
        
    def to_json(self) -> str:
        """Convert workflow to JSON"""
        return json.dumps(self.to_dict(), indent=2)
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Workflow':
        """Create workflow from dictionary"""
        workflow = cls(
            name=data["name"],
            description=data.get("description"),
            steps=[WorkflowStep.from_dict(step_data) for step_data in data.get("steps", [])],
            variables=data.get("variables", {}),
            on_success=data.get("on_success"),
            on_failure=data.get("on_failure"),
            max_concurrent_steps=data.get("max_concurrent_steps", 1)
        )
        
        # Restore workflow ID if available
        if "id" in data:
            workflow.id = data["id"]
            
        # Restore status if available
        if "status" in data:
            workflow.status = WorkflowStatus(data["status"])
            
        # Restore timing information
        if "created_at" in data:
            workflow.created_at = datetime.fromisoformat(data["created_at"])
        if "started_at" in data and data["started_at"]:
            workflow.started_at = datetime.fromisoformat(data["started_at"])
        if "completed_at" in data and data["completed_at"]:
            workflow.completed_at = datetime.fromisoformat(data["completed_at"])
            
        # Restore current step index
        workflow.current_step_index = data.get("current_step_index", 0)
        
        return workflow
        
    @classmethod
    def from_yaml(cls, yaml_str: str) -> 'Workflow':
        """Create workflow from YAML"""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)
        
    @classmethod
    def from_json(cls, json_str: str) -> 'Workflow':
        """Create workflow from JSON"""
        data = json.loads(json_str)
        return cls.from_dict(data)
        
    @classmethod
    def load_from_file(cls, file_path: str) -> 'Workflow':
        """Load workflow from file (YAML or JSON)"""
        with open(file_path, 'r') as f:
            content = f.read()
            
        if file_path.endswith('.yaml') or file_path.endswith('.yml'):
            return cls.from_yaml(content)
        elif file_path.endswith('.json'):
            return cls.from_json(content)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")
            
    def save_to_file(self, file_path: str) -> None:
        """Save workflow to file (YAML or JSON)"""
        if file_path.endswith('.yaml') or file_path.endswith('.yml'):
            content = self.to_yaml()
        elif file_path.endswith('.json'):
            content = self.to_json()
        else:
            raise ValueError(f"Unsupported file format: {file_path}")
            
        with open(file_path, 'w') as f:
            f.write(content)
            
        logger.info(f"Workflow saved to {file_path}")

class WorkflowEngine:
    """Engine for executing and managing workflows"""
    
    def __init__(self, workflows_dir: str = "workflows"):
        self.workflows_dir = workflows_dir
        os.makedirs(workflows_dir, exist_ok=True)
        
        # Create subdirectories for different workflow states
        self.active_dir = os.path.join(workflows_dir, "active")
        self.completed_dir = os.path.join(workflows_dir, "completed")
        self.failed_dir = os.path.join(workflows_dir, "failed")
        
        os.makedirs(self.active_dir, exist_ok=True)
        os.makedirs(self.completed_dir, exist_ok=True)
        os.makedirs(self.failed_dir, exist_ok=True)
        
        # Initialize browser agent
        self.browser_agent = BrowserAgent()
        
        # Initialize action registry
        self.action_registry = self._build_action_registry()
        
        # Initialize circuit breaker for workflow execution
        self.workflow_circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
        
        # Initialize thread pool for concurrent step execution
        self.thread_pool = {}  # Maps workflow ID to list of threads
        self.results_queue = queue.Queue()
        
        logger.info(f"Workflow engine initialized with directory: {workflows_dir}")
        
    def _build_action_registry(self) -> Dict[str, Callable]:
        """Build registry of available actions"""
        return {
            # Browser actions
            "open_browser": self.browser_agent.open_browser,
            "navigate_to": self.browser_agent.navigate_to,
            "click_image": self.browser_agent.click_on_image,
            "click_text": self.browser_agent.click_on_text,
            "type_text": self.browser_agent.type_text,
            "press_key": self.browser_agent.press_key,
            "take_screenshot": self.browser_agent.take_screenshot,
            "find_image": self.browser_agent.find_on_screen,
            "find_text": self.browser_agent.find_text_on_screen,
            "extract_text": self.browser_agent.extract_all_text,
            "detect_ui": self.browser_agent.detect_ui_elements,
            
            # Workflow control actions
            "wait": lambda seconds: time.sleep(float(seconds)),
            "set_variable": self._action_set_variable,
            "if_condition": self._action_if_condition,
            "loop": self._action_loop,
            "execute_workflow": self.execute_workflow_by_name
        }
        
    def _action_set_variable(self, workflow: Workflow, name: str, value: Any) -> None:
        """Action to set a workflow variable"""
        workflow.variables[name] = value
        return value
        
    def _action_if_condition(self, workflow: Workflow, condition: str, then_action: str, else_action: str = None) -> Any:
        """Action to execute conditional logic"""
        # Simple condition evaluation - in a real implementation, this would be more sophisticated
        condition_result = eval(condition, {"__builtins__": {}}, workflow.variables)
        
        if condition_result:
            if then_action in self.action_registry:
                return self.action_registry[then_action]()
        elif else_action and else_action in self.action_registry:
            return self.action_registry[else_action]()
            
        return condition_result
        
    def _action_loop(self, workflow: Workflow, items: List[Any], action: str, action_params: Dict[str, Any]) -> List[Any]:
        """Action to execute a loop"""
        results = []
        for item in items:
            # Add the current item to action params
            params = action_params.copy()
            params["item"] = item
            
            # Execute the action for this item
            if action in self.action_registry:
                result = self.action_registry[action](**params)
                results.append(result)
                
        return results
        
    def create_workflow(self, name: str, description: str = None) -> Workflow:
        """Create a new workflow"""
        workflow = Workflow(name=name, description=description)
        
        # Save the workflow
        file_path = os.path.join(self.active_dir, f"{workflow.id}.yaml")
        workflow.save_to_file(file_path)
        
        logger.info(f"Created workflow: {name} (ID: {workflow.id})")
        return workflow
        
    def load_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Load a workflow by ID"""
        # Check active workflows
        file_path = os.path.join(self.active_dir, f"{workflow_id}.yaml")
        if os.path.exists(file_path):
            return Workflow.load_from_file(file_path)
            
        # Check completed workflows
        file_path = os.path.join(self.completed_dir, f"{workflow_id}.yaml")
        if os.path.exists(file_path):
            return Workflow.load_from_file(file_path)
            
        # Check failed workflows
        file_path = os.path.join(self.failed_dir, f"{workflow_id}.yaml")
        if os.path.exists(file_path):
            return Workflow.load_from_file(file_path)
            
        logger.warning(f"Workflow not found: {workflow_id}")
        return None
        
    def load_workflow_by_name(self, name: str) -> Optional[Workflow]:
        """Load a workflow by name (returns the most recent one if multiple exist)"""
        workflows = []
        
        # Check all directories
        for directory in [self.active_dir, self.completed_dir, self.failed_dir]:
            for filename in os.listdir(directory):
                if filename.endswith('.yaml') or filename.endswith('.yml'):
                    file_path = os.path.join(directory, filename)
                    workflow = Workflow.load_from_file(file_path)
                    if workflow.name == name:
                        workflows.append((workflow, file_path))
                        
        if not workflows:
            logger.warning(f"No workflows found with name: {name}")
            return None
            
        # Sort by creation time (most recent first)
        workflows.sort(key=lambda x: x[0].created_at, reverse=True)
        return workflows[0][0]
        
    def list_workflows(self, status: WorkflowStatus = None) -> List[Workflow]:
        """List all workflows, optionally filtered by status"""
        workflows = []
        
        # Determine which directories to check based on status
        if status == WorkflowStatus.COMPLETED:
            directories = [self.completed_dir]
        elif status == WorkflowStatus.FAILED:
            directories = [self.failed_dir]
        elif status == WorkflowStatus.PENDING or status == WorkflowStatus.RUNNING:
            directories = [self.active_dir]
        else:
            directories = [self.active_dir, self.completed_dir, self.failed_dir]
            
        # Load workflows from directories
        for directory in directories:
            for filename in os.listdir(directory):
                if filename.endswith('.yaml') or filename.endswith('.yml'):
                    file_path = os.path.join(directory, filename)
                    workflow = Workflow.load_from_file(file_path)
                    
                    # Filter by status if specified
                    if status is None or workflow.status == status:
                        workflows.append(workflow)
                        
        return workflows
        
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow by ID"""
        # Check all directories
        for directory in [self.active_dir, self.completed_dir, self.failed_dir]:
            file_path = os.path.join(directory, f"{workflow_id}.yaml")
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted workflow: {workflow_id}")
                return True
                
        logger.warning(f"Workflow not found for deletion: {workflow_id}")
        return False
        
    def _execute_step(self, workflow: Workflow, step: WorkflowStep) -> None:
        """Execute a single workflow step"""
        try:
            # Update step status
            step.status = StepStatus.RUNNING
            step.start_time = datetime.now()
            
            # Save workflow state
            self._save_workflow_state(workflow)
            
            logger.info(f"Executing step: {step.id} ({step.action})")
            
            # Check if action exists
            if step.action not in self.action_registry:
                raise ValueError(f"Unknown action: {step.action}")
                
            # Apply retry decorator based on step configuration
            @retry(
                max_attempts=step.retry_config.get("max_attempts", 3),
                delay=step.retry_config.get("delay", 1.0),
                backoff_factor=step.retry_config.get("backoff_factor", 1.5)
            )
            def execute_with_retry():
                # Get the action function
                action_func = self.action_registry[step.action]
                
                # Execute with timeout
                result = action_func(**step.params)
                return result
                
            # Execute the step with retry
            result = execute_with_retry()
            
            # Update step status
            step.status = StepStatus.COMPLETED
            step.result = result
            step.end_time = datetime.now()
            
            # Put result in queue for main thread to process
            self.results_queue.put((workflow.id, step.id, True, result, None))
            
        except Exception as e:
            logger.error(f"Error executing step {step.id}: {e}")
            
            # Update step status
            step.status = StepStatus.FAILED
            step.error = str(e)
            step.end_time = datetime.now()
            
            # Put error in queue for main thread to process
            self.results_queue.put((workflow.id, step.id, False, None, e))
            
    def _save_workflow_state(self, workflow: Workflow) -> None:
        """Save the current state of a workflow"""
        # Determine the appropriate directory based on workflow status
        if workflow.status == WorkflowStatus.COMPLETED:
            directory = self.completed_dir
        elif workflow.status == WorkflowStatus.FAILED:
            directory = self.failed_dir
        else:
            directory = self.active_dir
            
        # Save workflow to file
        file_path = os.path.join(directory, f"{workflow.id}.yaml")
        workflow.save_to_file(file_path)
        
    def _process_results_queue(self) -> None:
        """Process results from the queue"""
        while not self.results_queue.empty():
            workflow_id, step_id, success, result, error = self.results_queue.get()
            
            # Load the workflow
            workflow = self.load_workflow(workflow_id)
            if not workflow:
                logger.error(f"Could not load workflow {workflow_id} to process results")
                continue
                
            # Find the step
            step = next((s for s in workflow.steps if s.id == step_id), None)
            if not step:
                logger.error(f"Could not find step {step_id} in workflow {workflow_id}")
                continue
                
            # Update step status
            if success:
                step.status = StepStatus.COMPLETED
                step.result = result
            else:
                step.status = StepStatus.FAILED
                step.error = str(error)
                
            # Save workflow state
            self._save_workflow_state(workflow)
            
    def execute_workflow(self, workflow: Workflow) -> None:
        """Execute a workflow"""
        try:
            # Use circuit breaker for workflow execution
            @self.workflow_circuit
            def _execute_workflow():
                # Update workflow status
                workflow.status = WorkflowStatus.RUNNING
                workflow.started_at = datetime.now()
                
                # Save workflow state
                self._save_workflow_state(workflow)
                
                logger.info(f"Executing workflow: {workflow.name} (ID: {workflow.id})")
                
                # Initialize thread pool for this workflow
                self.thread_pool[workflow.id] = []
                
                # Execute steps sequentially
                for i, step in enumerate(workflow.steps):
                    # Skip already completed steps
                    if step.status == StepStatus.COMPLETED:
                        continue
                        
                    # Update current step index
                    workflow.current_step_index = i
                    
                    # Check if we should execute this step concurrently
                    if workflow.max_concurrent_steps > 1 and len(self.thread_pool[workflow.id]) < workflow.max_concurrent_steps:
                        # Create thread for step execution
                        thread = threading.Thread(
                            target=self._execute_step,
                            args=(workflow, step)
                        )
                        thread.start()
                        self.thread_pool[workflow.id].append(thread)
                    else:
                        # Execute step in current thread
                        self._execute_step(workflow, step)
                        
                    # Process any results that have come in
                    self._process_results_queue()
                    
                    # Check if workflow should continue
                    if step.status == StepStatus.FAILED:
                        # Handle error based on step configuration
                        if step.error_handler:
                            # TODO: Implement error handlers
                            pass
                        else:
                            # Mark workflow as failed
                            workflow.status = WorkflowStatus.FAILED
                            workflow.completed_at = datetime.now()
                            
                            # Move workflow file to failed directory
                            self._save_workflow_state(workflow)
                            
                            logger.error(f"Workflow failed: {workflow.name} (ID: {workflow.id})")
                            return False
                            
                # Wait for any remaining threads to complete
                if workflow.id in self.thread_pool:
                    for thread in self.thread_pool[workflow.id]:
                        thread.join()
                    
                    # Process any remaining results
                    self._process_results_queue()
                    
                    # Clean up thread pool
                    del self.thread_pool[workflow.id]
                    
                # Check if all steps completed successfully
                all_completed = all(step.status == StepStatus.COMPLETED for step in workflow.steps)
                
                if all_completed:
                    # Mark workflow as completed
                    workflow.status = WorkflowStatus.COMPLETED
                    workflow.completed_at = datetime.now()
                    
                    # Move workflow file to completed directory
                    self._save_workflow_state(workflow)
                    
                    logger.info(f"Workflow completed successfully: {workflow.name} (ID: {workflow.id})")
                    
                    # Execute on_success handler if defined
                    if workflow.on_success:
                        # TODO: Implement success handlers
                        pass
                        
                    return True
                else:
                    # Mark workflow as failed
                    workflow.status = WorkflowStatus.FAILED
                    workflow.completed_at = datetime.now()
                    
                    # Move workflow file to failed directory
                    self._save_workflow_state(workflow)
                    
                    logger.error(f"Workflow failed: {workflow.name} (ID: {workflow.id})")
                    
                    # Execute on_failure handler if defined
                    if workflow.on_failure:
                        # TODO: Implement failure handlers
                        pass
                        
                    return False
                    
            # Execute workflow with circuit breaker
            result = _execute_workflow()
            if result is None:  # Circuit is open
                logger.warning(f"Workflow circuit is open, execution skipped for: {workflow.name}")
                workflow.status = WorkflowStatus.FAILED
                workflow.completed_at = datetime.now()
                self._save_workflow_state(workflow)
                
        except Exception as e:
            logger.error(f"Error executing workflow {workflow.name}: {e}")
            
            # Mark workflow as failed
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = datetime.now()
            self._save_workflow_state(workflow)
            
    def execute_workflow_by_id(self, workflow_id: str) -> None:
        """Execute a workflow by ID"""
        workflow = self.load_workflow(workflow_id)
        if workflow:
            self.execute_workflow(workflow)
        else:
            logger.error(f"Workflow not found: {workflow_id}")
            
    def execute_workflow_by_name(self, name: str) -> None:
        """Execute a workflow by name"""
        workflow = self.load_workflow_by_name(name)
        if workflow:
            self.execute_workflow(workflow)
        else:
            logger.error(f"Workflow not found: {name}")
            
    def create_browser_workflow(self, name: str, url: str) -> Workflow:
        """Create a simple browser workflow"""
        workflow = self.create_workflow(name, f"Browser workflow to navigate to {url}")
        
        # Add steps
        workflow.add_step(WorkflowStep(
            id=str(uuid.uuid4()),
            action="open_browser",
            params={"browser": "chrome"},
            description="Open Chrome browser"
        ))
        
        workflow.add_step(WorkflowStep(
            id=str(uuid.uuid4()),
            action="navigate_to",
            params={"url": url},
            description=f"Navigate to {url}"
        ))
        
        workflow.add_step(WorkflowStep(
            id=str(uuid.uuid4()),
            action="take_screenshot",
            params={"filename": f"{name}_screenshot.png"},
            description="Take screenshot of the page"
        ))
        
        # Save the workflow
        self._save_workflow_state(workflow)
        
        logger.info(f"Created browser workflow: {name} (ID: {workflow.id})")
        return workflow
        
    def create_data_extraction_workflow(self, name: str, url: str) -> Workflow:
        """Create a workflow to extract data from a webpage"""
        workflow = self.create_workflow(name, f"Data extraction workflow for {url}")
        
        # Add steps
        workflow.add_step(WorkflowStep(
            id=str(uuid.uuid4()),
            action="open_browser",
            params={"browser": "chrome"},
            description="Open Chrome browser"
        ))
        
        workflow.add_step(WorkflowStep(
            id=str(uuid.uuid4()),
            action="navigate_to",
            params={"url": url},
            description=f"Navigate to {url}"
        ))
        
        workflow.add_step(WorkflowStep(
            id=str(uuid.uuid4()),
            action="extract_text",
            params={},
            description="Extract all text from the page"
        ))
        
        workflow.add_step(WorkflowStep(
            id=str(uuid.uuid4()),
            action="detect_ui",
            params={},
            description="Detect UI elements on the page"
        ))
        
        workflow.add_step(WorkflowStep(
            id=str(uuid.uuid4()),
            action="take_screenshot",
            params={"filename": f"{name}_screenshot.png"},
            description="Take screenshot of the page"
        ))
        
        # Save the workflow
        self._save_workflow_state(workflow)
        
        logger.info(f"Created data extraction workflow: {name} (ID: {workflow.id})")
        return workflow

# Example workflow definition in YAML format
EXAMPLE_WORKFLOW_YAML = """
name: Google Search Example
description: A workflow to perform a Google search
variables:
  search_term: "computer vision"
steps:
  - id: step1
    action: open_browser
    params:
      browser: chrome
    description: Open Chrome browser
    timeout: 30
    retry_config:
      max_attempts: 3
      delay: 1.0
      backoff_factor: 1.5
  
  - id: step2
    action: navigate_to
    params:
      url: "https://www.google.com"
    description: Navigate to Google
    timeout: 30
  
  - id: step3
    action: type_text
    params:
      text: "${search_term}"
    description: Type search term
    timeout: 10
  
  - id: step4
    action: press_key
    params:
      key: "enter"
    description: Press Enter to search
    timeout: 10
  
  - id: step5
    action: take_screenshot
    params:
      filename: "google_search_results.png"
    description: Take screenshot of search results
    timeout: 10
"""

# Example usage
if __name__ == "__main__":
    # Initialize workflow engine
    engine = WorkflowEngine()
    
    # Create a workflow from YAML
    workflow = Workflow.from_yaml(EXAMPLE_WORKFLOW_YAML)
    
    # Save the workflow
    file_path = os.path.join(engine.active_dir, f"{workflow.id}.yaml")
    workflow.save_to_file(file_path)
    
    # Execute the workflow
    engine.execute_workflow(workflow)

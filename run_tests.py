#!/usr/bin/env python3
"""
Test runner for Computer Control Agent
Runs all tests with coverage reporting
"""

import os
import sys
import unittest
import coverage
import argparse
import logging
import unittest.mock as mock

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_runner')

def run_tests(test_pattern=None, verbose=False, html_report=True):
    """Run all tests with coverage reporting"""
    # Start coverage
    cov = coverage.Coverage(
        source=['agent.py', 'browser_agent.py', 'mcp_server.py', 'mcp_client.py', 
                'resilience.py', 'computer_vision.py', 'workflow.py', 'monitoring.py', 
                'dashboard.py'],
        omit=['*/__pycache__/*', '*/test_*.py', '*/tests/*']
    )
    cov.start()
    
    try:
        # Apply mock patches for PyAutoGUI
        pyautogui_mock = mock.MagicMock()
        pyautogui_mock.click = mock.MagicMock(return_value=None)
        pyautogui_mock.moveTo = mock.MagicMock(return_value=None)
        pyautogui_mock.typewrite = mock.MagicMock(return_value=None)
        pyautogui_mock.screenshot = mock.MagicMock(return_value=mock.MagicMock())
        
        # Apply patches
        with mock.patch.dict('sys.modules', {'pyautogui': pyautogui_mock}):
            # Discover and run tests
            loader = unittest.TestLoader()
            
            if test_pattern:
                logger.info(f"Running tests matching pattern: {test_pattern}")
                suite = loader.discover('tests', pattern=f'test_{test_pattern}.py')
            else:
                logger.info("Running all tests")
                suite = loader.discover('tests', pattern='test_*.py')
            
            # Configure test runner
            verbosity = 2 if verbose else 1
            runner = unittest.TextTestRunner(verbosity=verbosity)
            
            # Run tests
            result = runner.run(suite)
        
        # Stop coverage
        cov.stop()
        cov.save()
        
        # Report coverage
        logger.info("Coverage Summary:")
        cov.report()
        
        # Generate HTML report
        if html_report:
            html_dir = os.path.join(os.path.dirname(__file__), 'coverage_html')
            logger.info(f"Generating HTML coverage report in {html_dir}")
            cov.html_report(directory=html_dir)
        
        # Return success/failure
        return result.wasSuccessful()
        
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        return False
        
if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run tests for Computer Control Agent')
    parser.add_argument('--pattern', '-p', help='Test pattern to run (e.g. "agent" for test_agent.py)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--no-html', action='store_true', help='Disable HTML coverage report')
    args = parser.parse_args()
    
    # Run tests
    success = run_tests(
        test_pattern=args.pattern,
        verbose=args.verbose,
        html_report=not args.no_html
    )
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

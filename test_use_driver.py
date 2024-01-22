# test_robot_driver.py
from driver import MockRobotDriver
import time
import pytest


@pytest.fixture
def robot_driver():
    # Create MockRobotDriver instance
    robot_driver = MockRobotDriver()

    # Open connection as part of setup
    # Could also set connected = True for testing
    connection_result = robot_driver.OpenConnection("192.168.49.1")
    assert connection_result == ""

    # Initialize as part of setup
    # Could also set homed = True for testing
    initialize_result = robot_driver.Initialize()
    assert initialize_result == ""

    # Return the initialized MockRobotDriver instance
    return robot_driver


def test_execute_pick_operation(robot_driver):
    pick1 = robot_driver.ExecuteOperation("Pick", ["Source Location"], [10])
    assert pick1 == ""


def test_execute_pick_operation_while_running(robot_driver):
    pick1 = robot_driver.ExecuteOperation("Pick", ["Source Location"], [10])
    assert pick1 == ""
    pick_same_time = robot_driver.ExecuteOperation("Pick", ["Source Location"], [5])
    assert "Error: Another process is already running" in pick_same_time


def test_execute_pick_operation_2(robot_driver):
    pick1 = robot_driver.ExecuteOperation("Pick", ["Source Location"], [10])
    # wait for completion
    time.sleep(5 * 60)
    pick2 = robot_driver.ExecuteOperation("Pick", ["Source Location"], [5])
    assert pick2 == ""


def test_execute_place_operation(robot_driver):
    place = robot_driver.ExecuteOperation("Place", ["Destination Location"], [10])
    assert place == ""


def test_execute_transfer_operation(robot_driver):
    transfer = robot_driver.ExecuteOperation("Transfer", ["Source Location", "Destination Location"], [12, 5])
    assert transfer == ""


def test_bad_params(robot_driver):
    # test bad operation
    transfer = robot_driver.ExecuteOperation("Make smoothie", ["Source Location", "Destination Location"], [12, 5])
    assert "Validation Error: Invalid operation" in transfer
    # test bad names
    transfer = robot_driver.ExecuteOperation("Transfer", ["Source", "Destination"], [12, 5])
    assert "Validation Error: Invalid parameter name" in transfer
    # test bad value
    transfer = robot_driver.ExecuteOperation("Transfer", ["Source Location", "Destination Location"], [122, 5])
    assert "Validation Error: Invalid parameter value" in transfer


def test_abort(robot_driver):
    abort = robot_driver.Abort()
    assert abort == ""

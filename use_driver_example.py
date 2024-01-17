from driver import  MockRobotDriver
import time

# Example of using the modified MockRobotDriver
robot_driver = MockRobotDriver()

# Open connection
connection_result = robot_driver.OpenConnection("192.168.1.1")
print(connection_result)

# Initialize
initialize_result = robot_driver.initialize()
print(initialize_result)

# Execute Pick operation
pick_result = robot_driver.execute_operation("Pick", ["Source Location"], [10])
print(pick_result)

# Attempt to execute another Pick operation while one is still running
pick_result_concurrent = robot_driver.execute_operation("Pick", ["Source Location"], [5])
print(pick_result_concurrent)  # This should return an error

# Wait for the first Pick operation to complete
time.sleep(5 * 60)

# Execute another Pick operation after the first one
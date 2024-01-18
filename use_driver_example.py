from driver import MockRobotDriver
import time

# Example of using the modified MockRobotDriver
robot_driver = MockRobotDriver()

# Open connection
connection_result = robot_driver.OpenConnection("192.168.1.1")
print(connection_result)

# Initialize
initialize_result = robot_driver.Initialize()
print(initialize_result)

# Execute Pick operation
pick1 = robot_driver.ExecuteOperation("Pick", ["Source Location"], [10])
print(pick1)

# Attempt to execute another Pick operation while one is still running
pick_same_time = robot_driver.ExecuteOperation("Pick", ["Source Location"], [5])
print(pick_same_time)  # This should return process running error

# Wait for Pick 1 to complete or timeout
time.sleep(5 * 60)

# Execute Pick 2
pick2 = robot_driver.ExecuteOperation("Pick", ["Source Location"], [5])
print(pick1)

# Wait for Pick 2 to complete or timeout
time.sleep(5 * 60)

# Execute Place
place = robot_driver.ExecuteOperation("Place", ["Destination Location"], [10])
print(place)

# Wait for Place to complete or timeout
time.sleep(5 * 60)

# Execute Transfer
transfer = robot_driver.ExecuteOperation("Transfer", ["Source Location", "Destination Location"], [12,5])
print(transfer)

# Execute Abort
abort = robot_driver.Abort()
print(abort)

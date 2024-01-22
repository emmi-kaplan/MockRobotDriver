MockRobot Device API

The MockRobot is a robotic arm that moves objects to and from various locations around a system.  The robot can be controlled remotely by sending the commands supplied in this document to the robot’s onboard software.  The software will open a socket on port 1000, which will accept commands sent over TCP/IP.
Commands sent to the robot should be in this format:  a string with the command name first, followed by a “%” symbol, then any parameters required for the command.  Note that the MockRobot can only perform one process at a time, and will return a negative processID for any commands to begin a process while another process is in progress, rejecting the new command.

The MockRobot’s onboard software will accept the following commands:
“home” – Takes no parameters.  Returns int, processID.  This command tells the robot to begin its homing process, which needs to complete before the robot can move samples, and may take up to two minutes.  The onboard software will immediately return a unique ID that can be used to track the status of the running Home process.
“pick” – Takes an int, sourceLocation.  Returns int, processID.  This command tells the robot to begin a process to pick up a sample from the provided sourceLocation.  The onboard software will immediately return a unique ID that can be used to track the status of the running Pick process.  The process may take up to five minutes.
 “place” – Takes an int, destinationLocation.  Returns int, processID.  This command tells the robot to begin a process to place a sample to the provided destinationLocation.  The onboard software will immediately return a unique ID that can be used to track the status of the running Pick process.  The process may take up to five minutes.
“status” – Takes an int, processID.  Returns a string, processStatus.  This command retrieves the status of the process specified by processID.  The returned processStatus will be a message from the following list:
In Progress
Finished Successfully
Terminated With Error






Device Driver Interface Details
The User Interface program allows a user to control a MockRobot by the command set described in this document, implemented by a Device Driver.  The user will press a button mapped to one of the Device Driver functions below after typing in any needed parameters.  The UI program requires that each function returns either an empty string if the operation completed successfully, or a string with a description of an error that occurred during the function call, which will be displayed to the user.
Interface Methods:
OpenConnection(string IPAddress)
When a user presses the “Open Connection” button, the UI calls this function and expects the Device Driver to establish a connection with the MockRobot onboard software.
The parameter IPAddress is the address at which the MockRobot software is running.
Initialize()
When a user presses the “Initialize” button, the UI calls this function and expects that the Device Driver will put the MockRobot into an automation-ready (homed) state.
ExecuteOperation(string operation, string[] parameterNames, string[] parameterValues)
When a user presses the “Execute Operation” button, the UI calls this function and expects that the Device Driver will perform an operation determined by the parameter operation.
For this challenge, valid operations include Pick, Place, and Transfer (a pick followed immediately by a place in a single operation).
parameterNames is an array that contains the name of each parameter to be used for the given operation.
parameterValues is an array that contains the value of each parameter to be used for the given operation.
The parameters parameterNames and parameterValues are parallel, meaning that the name of a parameter and its value will be found at the same index of the two arrays.
For this challenge, you can expect “Source Location” and “Destination Location” to be the parameters sent from SchedulerProgram, as needed by the MockRobot API.
Examples of ExecuteOperation Calls:
ExecuteOperation(“Pick”, [Source Location], [10])
ExecuteOperation(“Transfer”, [Destination Location, Source Location], [5, 12])
ExecuteOperation(“Transfer”, [ Source Location, Destination Location], [12,5])
Note that 2 and 3 should result in the same behavior.
Abort()
When a user presses the “Abort” button, the UI calls this function and expects that the Device Driver will terminate communication with the MockRobot.

During normal operation, a user should select Open Connection once, Initialize once, then ExecuteOperation any number of times, and Abort could be called in between any of these calls.  Be aware though that a user could accidentally press buttons in an incorrect order.  Your driver design should have a way to handle this gracefully.
It is also possible that a user may send an invalid operation, or similarly the parameterNames/Values they provide may not contain the entries required for the MockRobot.  Your driver design should be able to catch these situations as well.

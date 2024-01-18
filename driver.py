# DO
# - Network manager

import time
from enum import Enum
import socket
import selectors
import logging

# Configure logging to print to external file (could print to console instead)
logging.basicConfig(filename='my_log_file.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# static error handling methods
def _not_connected_error():
    """ Static method for responding to a process request when the robot is not connected"""
    message = "Error: MockRobot is not connected. Press 'Open Connection' and then try your request again."
    logging.error(message)
    return message


def _process_running_error(current_process):
    """ Static method for responding to a process request when a current process is running"""
    message = f"Error: Another process is already running (process_id:{current_process}). " \
              f"Please wait for it to complete and try again"
    logging.error(message)
    return message


class Operation(Enum):
    """ Valid operations to be received from the UI """
    PICK = "Pick"
    PLACE = "Place"
    TRANSFER = "Transfer"


class ProcessStatus(Enum):
    """ Valid status responses to be received from robot status request """
    IN_PROGRESS = "In Progress"
    FINISHED_SUCCESSFULLY = "Finished Successfully"
    TERMINATED_WITH_ERROR = "Terminated With Error"


class MockRobotDriver:
    """
    Driver for the MockRobot, a robotic arm that moves objects to and from various locations around a system.
    The robot can be controlled remotely by sending the commands pick, place, or transfer from the UI
    to be formatted for the robot’s onboard-software.
    """

    def __init__(self):
        self.connected = False
        self.ip_address = None
        self.homed = False
        self.current_process = None
        self.port = 1000
        self.socket = None
        self.selector = selectors.DefaultSelector()
        self.valid_names = ["Destination Location", "Source Location"]
        # I made up this range :)
        self.valid_range = range(1,18)

    # UI mapped functions
    def OpenConnection(self, ip_address):
        """
        UI mapped function. When a user presses the “Open Connection” button, the UI calls this function and
        expects the Device Driver to establish a connection with the MockRobot onboard software.
        The software will open a socket on port 1000, which will accept commands sent over TCP/IP.
            Parameters:
                    ip_address (str): IP address used for connection ex. "127.0.0.1"
            Returns:
                    Empty String : If no error is encountered, an empty string is returned
        """
        logging.info(f"OpenConnection call. ip_address: {ip_address}")
        if self.connected:
            return f"Connection already open on {self.ip_address}." \
                   f" Press 'Abort' to close the current connection before attempting to establish a new one"
        # Attempt to open a connection
        try:
            logging.info(f"Connecting to {ip_address}...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)  # Set a timeout of 5 seconds
            self.socket.connect((ip_address, self.port))
            time.sleep(1)
            # We're assuming that if we don't encounter an error, the connection was successful
            # Check connection? Future implementation to actually check connection here... Status request?
            logging.info(f"Connection established on IP address: {ip_address}, port: {self.port}.")
        except Exception as e:
            # Handle any exceptions that might occur
            self.socket.close()
            logging.error(f"Error: Failed to connect: {str(e)}")
            return f"Error: Failed to connect: {str(e)} Make sure the robot is on and connected power."
        self.connected = True
        self.ip_address = ip_address
        # Register the socket for read events
        self.selector.register(self.socket, selectors.EVENT_READ)
        return ""

    def Initialize(self):
        """
        UI mapped function. When a user presses the “Initialize” button, the UI calls this function and expects that
        the Device Driver will put the MockRobot into an automation-ready (homed) state.
            Returns:
                    "" : If no error is encountered, an empty string is returned
        """
        logging.info("Initialize call from UI")
        if not self.connected:
            return _not_connected_error()
        if self.homed:
            logging.warning("MockRobot already initialized.")
            self.homed = False
            # I decided we should let them home more than once
            # return "Error: MockRobot already initialized."
        # Send Initialize command to MockRobot
        response = self.try_process("home")
        # If response is a Process_id, Initialization process commenced successfully. Monitor for completion
        if isinstance(response, int):
            process_id = response
            logging.info(f"Initialization process started. ProcessID: {process_id}")
            # Monitor status of process, timeout after 2 minutes
            status = self.monitor_process_completion(process_id, 120)
            if status == ProcessStatus.FINISHED_SUCCESSFULLY:
                # track whether the robot has been homed for future processes
                self.homed = True
                logging.info(f"Initialization process: {process_id} finished successfully!")
                return ""
            # The process started but errored before it finished, return error
            else:
                return f"Initialization started but program errored before completion: {status}"
        # Not an int means an error was encountered before the process started, return that error
        else:
            logging.error(f"{response}")
            return f"Initialization not started: {response}"

    def ExecuteOperation(self, operation, parameter_names, parameter_values):
        """
        UI mapped function. When a user presses the “Execute Operation” button, the UI calls this function and expects
        that the Device Driver will perform an operation determined by the parameter operation.
        Checks the instrument for ready state and parses the operation information into the correct robotic command
            Parameters:
                    operation (Operation): a string of enum type Operation defining which operation is to be completed
                    parameter_names ([str]):  array containing the name of each parameter to be used for the transfer
                    parameter_values ([int]): array containing the value of each parameter to be used for the transfer
            Returns:
                    "" : If no error is encountered, an empty string is returned
        """
        logging.info(f"ExecuteOperation call from UI. "
                     f"operation: {operation}, "
                     f"parameter_names: {parameter_names}, "
                     f"parameter_values: {parameter_values}")

        # Check if instrument is connected before sending request.
        if not self.connected:
            return _not_connected_error()

        # Check if instrument has been initialized before sending request.
        if not self.homed:
            logging.error("Error: MockRobot is not initialized. Press 'Initialize' and then try your request again.")
            return "Error: MockRobot is not initialized. Press 'Initialize' and then try your request again."

        # Check if there is current process running
        if self.current_process is not None:
            return _process_running_error(self.current_process)

        # Validate inputs
        valid = self.validate_inputs(operation, parameter_names, parameter_values)
        if valid[0]:
            logging.info(valid[1])
        else:
            logging.error(valid[1])
            # returns validation error to end program
            return valid[1]

        # returns empty string if successful or error message if not
        if operation == Operation.PICK:
            return self.pick(parameter_values[0])
        elif operation == Operation.PLACE:
            return self.place(parameter_values[0])
        elif operation == Operation.TRANSFER:
            return self.transfer(parameter_names, parameter_values)

    def Abort(self):
        """
        UI mapped function. When a user presses the “Abort” button, the UI calls this function and expects
        that the Device Driver will terminate communication with the MockRobot.
        Checks the instrument for ready state, then aborts communication and resets connection parameters
            Returns:
                    "" : If no error is encountered, an empty string is returned
        """
        logging.info("Initialize call from UI")
        if not self.connected:
            return _not_connected_error()
        if self.current_process is not None:
            return _process_running_error()

        # Abort communication and reset connection parameters
        self.socket.close()
        self.connected = False
        self.ip_address = None
        self.homed = False
        logging.info("Connection aborted successfully!")
        return ""

    # Helper functions
    def validate_inputs(self, operation, parameter_names, parameter_values):
        """
        UI mapped function. When a user presses the “Execute Operation” button, the UI calls this function and expects
        that the Device Driver will perform an operation determined by the parameter operation.
        Checks the instrument for ready state and parses the operation information into the correct robotic command
            Parameters:
                    operation (Operation): a string of enum type Operation defining which operation is to be completed
                    parameter_names ([str]):  array containing the name of each parameter to be used for the transfer
                    parameter_values ([int]): array containing the value of each parameter to be used for the transfer
            Returns:
                    (bool, str) : True for valid false for invalid, Validation error or validation success message
        """
        # validate operation
        if not isinstance(operation, Operation):
            logging.error("Validation Error: Invalid operation. Supported operations are Pick, Place, and Transfer.")
            return False, "Validation Error: Invalid operation. Supported operations are Pick, Place, and Transfer."
        # validate parameter names
        for name in parameter_names:
            if name not in self.valid_names:
                logging.error(f"Validation Error: Invalid parameter name: {name}. Select from valid names: {self.valid_names}")
                return False, f"Validation Error: Invalid parameter name: {name}. Select from valid names: {self.valid_names}"
        # validate parameter values
        for value in parameter_values:
            if value not in self.valid_range:
                logging.error(f"Validation Error: Invalid parameter value: {value}. Select from valid range: {self.valid_range}")
                return False, f"Validation Error: Invalid parameter value: {value}. Select from valid range: {self.valid_range}"

        # add any other validation here.
        # Can you pick and place to/from same location?
        # Can you place before you pick?

        return True, "Inputs validated"

    def try_process(self, command, timeout):
        """
        The driver will attempt to send a command to the robot onboard-software and record response.
        If successful, the robot response will be set as self.process_id
            Parameters:
                    command (str): command name first, followed by a “%” symbol, then any parameters required
                        ex. "pick%10"
                    timeout (int): timeout time in seconds to wait for process to complete
            Returns:
                    "" : If no error is encountered and the process completed, an empty string is returned.
                        Otherwise, error string is returned

        """
        try:
            # Send command to the robot's onboard software
            self.socket.send(command.encode())
            logging.info(f"Command sent: {command}")
            # Wait for the socket to be ready for response
            events = self.selector.select(timeout=1)
            if events:
                response = self.socket.recv(1024).decode()
                # The only int response is process id
                if isinstance(response, int):
                    process_id = response
                    # this is the process already running case (negative process_id)
                    if process_id < 0:
                        return _process_running_error(self.current_process)
                    # non-negative process_id means the process started successfully
                    self.current_process = process_id
                    logging.info(f"Process started. ProcessID: {process_id}")
                # response in unknown, throw an error
                else:
                    return f"Error: Unknown response: {response}"
            else:
                return "Error: Timeout waiting for response."
        # this should catch commands that are an invalid format
        except Exception as e:
            return f"Error: Failed to start process: {str(e)}"

        # now that we know the process started, we monitor for completion
        status = self.monitor_process_completion(process_id, 300)
        if status == ProcessStatus.FINISHED_SUCCESSFULLY:
            logging.info(f"Process: {process_id} finished successfully!")
            return ""

    def pick(self, source_location):
        """
        Formats the pick command before sending it to the robot software.
            Parameters:
                    source_location (int): location to pick from
            Returns:
                    "" : If no error is encountered, an empty string is returned.
                        Otherwise, error string is returned
        """
        # Pick command takes one parameter (int)
        command = f"pick%{source_location}"
        # Send Pick command to MockRobot, timeout after 5 minutes
        response = self.try_process(command, 300)
        # If response is not "", an error occurred. Log error
        if response != "":
            logging.error(f"Pick command failed: {response}")
            # return specific error
            return f"Pick command failed: {response}"
        else:
            # successful pick
            return ""

    def place(self, destination_location):
        """
        Formats the place command before sending it to the robot software.
            Parameters:
                    destination_location (int): location to place to
            Returns:
                    "" : If no error is encountered, an empty string is returned.
                        Otherwise, error string is returned
        """
        # Place command takes one parameter (int)
        command = f"place%{destination_location}"
        # Send Place command to MockRobot, timeout after 5 minutes
        response = self.try_process(command, 300)
        # If response is not "", an error occurred. Log error
        if response != "":
            logging.error(f"Place command failed: {response}")
            # return specific error
            return f"Place command failed: {response}"
        else:
            # successful place
            return ""

    def transfer(self, parameter_names, parameter_values):
        """
        Separates the transfer command into a pick and a place, executing both back to back.
        Parameter values are assigned as source or destination locations based on the parameter name order
            Parameters:
                    parameter_names ([str]):  array containing the name of each parameter to be used for the transfer
                    parameter_values ([int]): array containing the value of each parameter to be used for the transfer
            Returns:
                    "" : If no error is encountered, an empty string is returned.
                        Otherwise, error string is returned
        """
        source_location = parameter_values[parameter_names.index("Source Location")]
        destination_location = parameter_values[parameter_names.index("Destination Location")]
        pick_response = self.pick(source_location)
        # If response is not "", Pick process errored, return error
        if pick_response != "":
            return pick_response
        # Otherwise we can move onto place
        place_response = self.place(destination_location)
        # Returns either error string or ""
        return place_response

    def monitor_process_completion(self, process_id, timeout) -> str:
        """
        Checks whether a process has completed in the allotted time
            Parameters:
                    process_id (int): the id of the process to check
                    timeout (int): the number of seconds till a timeout error is called
            Returns:
                status (str): the status of the process if error, timeout, or completed
        """

        if self.current_process is None:
            return "Error: Current process is None. Unexpected state."

        # Initialize status to IN_PROGRESS
        status = ProcessStatus.IN_PROGRESS

        # start a timer
        t0 = t1 = time.time()
        while status != ProcessStatus.FINISHED_SUCCESSFULLY:
            # check every ten seconds? we could make this variable too
            time.sleep(10)
            status = self.get_status(process_id)
            # this case also catches the Terminated with Error response
            if status == ProcessStatus.TERMINATED_WITH_ERROR:
                self.current_process = None
                return f"Error, process terminated with error: {status}"
            elif status.contains("Error"):
                return f"Error, process status could not be retrieved: {status}"
            t1 = time.time()
            if t1-t0 > timeout:
                return "Error: Process timeout. Consider hard reset of instrument."
        # if a process completes, record that there is no current process running
        self.current_process = None
        return status  # status should be finished successfully by this point

    def get_status(self, process_id):
        """
        Formats the pick command before sending it to the robot software.
            Parameters:
                    process_id (int): the id of the process to check the status of.
                    This is assigned when a process starts
            Returns:
                    status : If no error is encountered, a known status is returned from the options
                    "In Progress", "Finished Successfully", or "Terminated With Error"

        """
        command = f"status%{process_id}"
        try:
            # Send command to the robot's onboard software
            self.socket.send(command.encode())
            logging.info(f"Checking status of process_id: {process_id}")
            # Wait for the socket to be ready for response
            events = self.selector.select(timeout=1)
            if events:
                response = self.socket.recv(1024).decode()
                logging.info(f"Status of process_id {process_id}: {response}")
                # Check if response is one of the known status responses
                if isinstance(response, ProcessStatus):
                    return response
                else:
                    return f"Error: Unexpected response: {response}"
            else:
                return "Error: Timeout waiting for response. Check connection."
        except Exception as e:
            return f"Error: Failed to retrieve status: {str(e)}"






import time
from enum import Enum
import socket
import selectors


# common error messages
def process_running_error(current_process):
    """
    Error message when a user attempts to start a process when one is already running
        Parameters:
                    current_process (int): current process identifier
        Returns:
                    Empty String : If no error is encountered, an empty string is returned
    """
    return f"Error: Another process is already running (Process ID: {current_process}). " \
           f"Please wait for it to complete and try again"


Not_connected_error = "Error: MockRobot is not connected. Press 'Open Connection' and then try your request again."
Not_initialized_error = "Error: MockRobot is not initialized. Press 'Initialize' and then try your request again."
Invalid_operation_error = "Error: Invalid operation. Supported operations are Pick, Place, and Transfer."


class Operation(Enum):
    """ Valid operations to be received from the UI """
    PICK = "Pick"
    PLACE = "Place"
    TRANSFER = "Transfer"


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

    def OpenConnection(self, ip_address):
        """
        The software will open a socket on port 1000, which will accept commands sent over TCP/IP.
            Parameters:
                    ip_address (str): IP address used for connection ex. "127.0.0.1"
            Returns:
                    Empty String : If no error is encountered, an empty string is returned
        """
        if self.connected:
            return f"Connection already open on {self.ip_address}." \
                   f" Press 'Abort' to close the current connection before attempting to establish a new one"
        # Attempt to open a connection
        try:
            print(f"Connecting to {ip_address}...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((ip_address, self.port))
            # Successful connection after a delay, is there a response from robot?
            time.sleep(1)
            print(f"Connection established on IP address: {ip_address}, port: {self.port}.")
        except Exception as e:
            # Handle any exceptions that might occur
            return f"Error: Failed to connect: {str(e)} Make sure the robot is on and connected power."
        self.connected = True
        self.ip_address = ip_address
        # Register the socket for read events
        self.selector.register(self.socket, selectors.EVENT_READ)
        return ""

    def try_process(self, command, duration=1):
        """
        The driver will attempt to send a command to the robot onboard-software and record response.
        If successful, the robot response will be set as self.process_id
            Parameters:
                    command (str): command name first, followed by a “%” symbol, then any parameters required
                    ex. "pick%10"
            Returns:
                    "" : If no error is encountered, an empty string is returned
        """
        try:
            # Send command to the robot's onboard software
            self.socket.send(command.encode())
            # Wait for the socket to be ready for response
            events = self.selector.select(timeout=duration)
            if events:
                response = self.socket.recv(1024).decode()
                if response.startswith("Error:"):
                    return response
                # this is the process already running case (negative process_id)
                elif response.startswith("-"):
                    return process_running_error(self.current_process)
                else:
                    process_id = int(response.split("%")[0])
                    self.current_process = process_id
                    print(f"Process started. ProcessID: {process_id}")
                    return ""
            else:
                return "Error: Timeout waiting for response."
        except Exception as e:
            return f"Error: Failed to initialize: {str(e)}"

    def Initialize(self):
        """
        When a user presses the “Initialize” button, the UI calls this function and expects that
        the Device Driver will put the MockRobot into an automation-ready (homed) state.
            Returns:
                    "" : If no error is encountered, an empty string is returned
        """
        if not self.connected:
            return Not_connected_error
        # I think this takes care of a process running error too...
        # cause a process couldn't be running if it weren't homed
        if self.homed:
            return "Error: MockRobot already initialized."
        # Home command takes no parameters
        command = "home"
        # Send Initialize command to MockRobot, timeout at 2 minutes
        self.try_process(command, 120)
        self.homed = True
        return ""

    def pick(self, source_location):
        """
        Formats the pick command before sending it to the robot software.
            Parameters:
                    source_location (int): location to pick from
            Returns:
                    "" : If no error is encountered, an empty string is returned
        """
        # Pick command takes one parameter (int)
        command = f"pick%{source_location}"
        # Send Pick command to MockRobot, timeout at 5 minutes
        self.try_process(command, 300)
        return ""

    def place(self, destination_location):
        """
        Formats the place command before sending it to the robot software.
            Parameters:
                    destination_location (int): location to place to
            Returns:
                    "" : If no error is encountered, an empty string is returned
        """
        # Place command takes one parameter (int)
        command = f"place%{destination_location}"
        # Send Place command to MockRobot, timeout at 5 minutes
        self.try_process(command, 300)
        return ""

    def transfer(self, parameter_names, parameter_values):
        """
        Separates the transfer command into a pick and a place, executing both back to back.
        Parameter values are assigned as source or destination locations based on the parameter name order
            Parameters:
                    parameter_names ([str]):  array containing the name of each parameter to be used for the transfer
                    parameter_values ([int]): array containing the value of each parameter to be used for the transfer
            Returns:
                    "" : If no error is encountered, an empty string is returned
        """
        source_location = parameter_values[parameter_names.index("Source Location")]
        destination_location = parameter_values[parameter_names.index("Destination Location")]
        self.pick(source_location)
        self.place(destination_location)
        return ""

    def ExecuteOperation(self, operation, parameter_names, parameter_values):
        """
        Checks the instrument for ready state and parses the operation information into the correct robotic command
            Parameters:
                    operation (Operation): a string of enum type Operation defining which operation is to be completed
                    parameter_names ([str]):  array containing the name of each parameter to be used for the transfer
                    parameter_values ([int]): array containing the value of each parameter to be used for the transfer
            Returns:
                    "" : If no error is encountered, an empty string is returned
        """
        if not self.connected:
            return Not_connected_error

        if not self.homed:
            return Not_initialized_error

        if self.current_process is not None:
            # future implementation of process timer or UI status checker
            return process_running_error(self.current_process)

        if not isinstance(operation, Operation):
            return Invalid_operation_error

        if operation == Operation.PICK:
            self.pick(parameter_values)
        elif operation == Operation.PLACE:
            self.place(parameter_values)
        elif operation == Operation.TRANSFER:
            self.transfer(parameter_names, parameter_values)

        # if we get here we can assume the process completed
        self.current_process = None
        return ""

    def abort(self):
        """
        Checks the instrument for ready state, then aborts communication and resets connection parameters
            Returns:
                    "" : If no error is encountered, an empty string is returned
        """
        if not self.connected:
            return "Error: No active connection to abort."
        if self.current_process is not None:
            return process_running_error(self.current_process)

        # Abort communication and reset connection parameters
        self.socket.close()
        self.connected = False
        self.ip_address = None
        self.homed = False
        self.current_process = None
        print("Connection aborted")
        return ""

    def status(self, process_id):
        if self.current_process == process_id:
            return "In Progress"
        return "Invalid Process ID"






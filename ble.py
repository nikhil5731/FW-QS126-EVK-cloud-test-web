import time
import queue
import asyncio
import threading
from bleak import *
from enum import IntEnum
import binascii
import atexit


# https://ambiq.com/wp-content/uploads/2022/03/AMDTP-Example-UsersGuide.pdf


class AMDTP_PKT_TYPE(IntEnum):
    UNKNOWN = 0
    DATA = 1
    ACK = 2
    CONTROL = 3
    MAX = 4


class AMDTP_CONTROL(IntEnum):
    RESEND_REQ = 0
    MAX = 1


class AMDTP_HEADER_BIT_OFFSET(IntEnum):
    ENABLE_ACK = 6
    ENCRYPTION = 7
    SN = 8
    TYPE = 12


class AMDTP_HEADER_BIT_MASK(IntEnum):
    ENABLE_ACK = 0b1
    ENCRYPTION = 0b1
    SN = 0b1111
    TYPE = 0b1111


class AMDTP_STATUS(IntEnum):
    SUCCESS = 0
    CRC_ERROR = 1
    INVALID_METADATA_INFO = 2
    INVALID_PKT_LENGTH = 3
    INSUFFICIENT_BUFFER = 4
    UNKNOWN_ERROR = 5
    BUSY = 6
    TX_NOT_READY = 7  # no connection or tx busy
    RESEND_REPLY = 8
    RECEIVE_CONTINUE = 9
    RECEIVE_DONE = 10
    MAX = 11


class AMDTP_CHAR_HANDLE(IntEnum):
    """
    Characteristic: 00002760-08c2-11e1-9073-0e8ac72e0011 (Handle: 2049): time (minute)
      Properties: ['write-without-response']
    Characteristic: 00002760-08c2-11e1-9073-0e8ac72e0012 (Handle: 2051): time (minute)
      Properties: ['notify']
      Descriptor: 00002902-0000-1000-8000-00805f9b34fb (Handle: 2053): Client Characteristic Configuration
    Characteristic: 00002760-08c2-11e1-9073-0e8ac72e0013 (Handle: 2054): time (minute)
      Properties: ['write-without-response', 'notify']
      Descriptor: 00002902-0000-1000-8000-00805f9b34fb (Handle: 2056): Client Characteristic Configuration
    """

    WRITE = 2049
    READ = 2051
    READ_CCCD = 2053
    ACK = 2054
    ACK_CCCD = 2056


class AMDTPPacket:
    """
    A class representing an AMDTP packet for BLE communication.

    Attributes:
        DATA_LEN_SIZE (int): Size of the data length field in bytes.
        HEADER_SIZE (int): Size of the header field in bytes.
        CRC_SIZE (int): Size of the CRC field in bytes.

    Methods:
        __init__(self) -> None:
            Initializes the AMDTPPacket object with default values.

        __str__(self) -> str:
            Returns a formatted string representation of the AMDTPPacket.

        unpack(self, packet: bytearray) -> AMDTP_STATUS:
            Unpacks the provided bytearray into the AMDTPPacket attributes.

        pack_data(self, data: list, sn: int) -> None:
            Packs the data into the AMDTPPacket for transmission as a data packet.

        pack_ack(self, status: AMDTP_STATUS) -> None:
            Packs the acknowledgment status into the AMDTPPacket for transmission.

        pack_control(self, control: AMDTP_CONTROL, serial_number: int) -> None:
            Packs the control information into the AMDTPPacket for transmission.

    Note:
        The AMDTPPacket class is designed for handling packet creation, unpacking, and packing
        for AMDTP (Ambiq Micro Data Transfer Protocol) communication over BLE.

    """

    DATA_LEN_SIZE = 2
    HEADER_SIZE = 2
    CRC_SIZE = 4

    def __init__(self) -> None:
        """
        Initializes the AMDTPPacket object with default values.
        """
        self.raw = None

        self.length = None
        self.header_ack = None  # TODO ???
        self.header_encrypted = None
        self.header_sn = None  # AMDTP_PKT_TYPE_DATA only
        self.header_type = None
        self.data = None
        self.crc = None

        self.crc_error = None

    def __str__(self) -> str:
        """
        Returns a formatted string representation of the AMDTPPacket.

        Returns:
            str: Formatted string representation of the AMDTPPacket.
        """
        output = ""
        output += f"length: {self.length}\n"
        output += f"header_ack: {self.header_ack}\n"
        output += f"header_encrypted: {self.header_encrypted}\n"
        output += f"header_sn: {self.header_sn}\n"
        output += f"header_type: {self.header_type}\n"
        output += f"data: {self.data}\n"
        output += f"crc: 0x{self.crc:08x}\n"
        output += f"crc_error: {self.crc_error}\n"

        return output

    def unpack(self, packet: bytearray) -> AMDTP_STATUS:
        """
        Unpacks the provided bytearray into the AMDTPPacket attributes.

        Args:
            packet (bytearray): The bytearray to unpack.

        Returns:
            AMDTP_STATUS: The status of the unpacking operation.

        Note:
            This method extracts and validates the information from the packet,
            including length, header, data, CRC, and CRC error status.

        """
        self.raw = packet
        i = 0

        # TODO: Handle other errors, see AMDTP_STATUS

        # Extract length from the packet
        self.length = int.from_bytes(packet[i : i + self.DATA_LEN_SIZE], byteorder="little", signed=False)

        # Validate if the length of the packet matches the encoded length in the header
        if (self.length + self.HEADER_SIZE + self.DATA_LEN_SIZE) != len(packet):
            return AMDTP_STATUS.INVALID_PKT_LENGTH

        # Calculate data length based on total length, header size, and data length size
        data_length = self.length - self.HEADER_SIZE - self.DATA_LEN_SIZE
        i += self.DATA_LEN_SIZE

        # Extract header information
        header = int.from_bytes(packet[i : i + self.HEADER_SIZE], byteorder="little", signed=False)
        self.header_ack = (header >> AMDTP_HEADER_BIT_OFFSET.ENABLE_ACK) & AMDTP_HEADER_BIT_MASK.ENABLE_ACK
        self.header_encrypted = (header >> AMDTP_HEADER_BIT_OFFSET.ENCRYPTION) & AMDTP_HEADER_BIT_MASK.ENCRYPTION
        self.header_sn = (header >> AMDTP_HEADER_BIT_OFFSET.SN) & AMDTP_HEADER_BIT_MASK.SN
        self.header_type = (header >> AMDTP_HEADER_BIT_OFFSET.TYPE) & AMDTP_HEADER_BIT_MASK.TYPE
        i += self.HEADER_SIZE

        # Extract data from the packet
        crc_start = i
        self.data = packet[i : i + data_length]
        i += data_length

        # Extract CRC from the packet
        self.crc = int.from_bytes(packet[i : i + self.CRC_SIZE], byteorder="little", signed=False)
        i += 4

        # Calculate CRC result for verification
        crc_result = binascii.crc32(packet[crc_start:-4])

        # Check for CRC error
        self.crc_error = self.crc != crc_result

        return AMDTP_STATUS.CRC_ERROR if self.crc_error else AMDTP_STATUS.SUCCESS

    def __pack(self) -> None:
        """
        Packs the AMDTPPacket attributes into a raw bytearray.

        Note:
            This private method is used to prepare the raw bytearray for transmission.
            It constructs the packet by combining length, header, data, and CRC information.
            The CRC is calculated and appended to the raw data.

        """
        # Convert length to bytes and assign to raw
        self.raw = self.length.to_bytes(2, byteorder="little", signed=False)

        # Construct the header by bitwise OR operations
        header = 0
        header |= (self.header_ack & AMDTP_HEADER_BIT_MASK.ENABLE_ACK) << AMDTP_HEADER_BIT_OFFSET.ENABLE_ACK
        header |= (self.header_encrypted & AMDTP_HEADER_BIT_MASK.ENCRYPTION) << AMDTP_HEADER_BIT_OFFSET.ENCRYPTION
        header |= (self.header_sn & AMDTP_HEADER_BIT_MASK.SN) << AMDTP_HEADER_BIT_OFFSET.SN
        header |= (self.header_type & AMDTP_HEADER_BIT_MASK.TYPE) << AMDTP_HEADER_BIT_OFFSET.TYPE

        # Append the header to raw
        self.raw += header.to_bytes(2, byteorder="little", signed=False)

        # Append data to raw (convert to bytearray if not already)
        self.raw += bytearray(self.data) if type(self.data) != bytearray else self.data

        # Calculate CRC and append to raw
        self.crc = binascii.crc32(self.raw[self.DATA_LEN_SIZE + self.HEADER_SIZE :])
        self.raw += self.crc.to_bytes(4, byteorder="little", signed=False)

    def pack_data(self, data: list, sn: int):
        """
        Packs the data into the AMDTPPacket for transmission as a data packet.

        Args:
            data (list): The data to be packed.
            sn (int): Serial number.

        """
        self.length = len(data) + self.CRC_SIZE
        self.header_ack = 0
        self.header_encrypted = 0
        self.header_sn = sn
        self.header_type = AMDTP_PKT_TYPE.DATA
        self.data = data
        self.crc = None

        self.__pack()

    def pack_ack(self, status: AMDTP_STATUS):
        """
        Packs the acknowledgment status into the AMDTPPacket for transmission.

        Args:
            status (AMDTP_STATUS): The acknowledgment status.

        """
        self.length = 1 + self.CRC_SIZE
        self.header_ack = 0
        self.header_encrypted = 0
        self.header_sn = 0
        self.header_type = AMDTP_PKT_TYPE.ACK
        self.data = [status]
        self.crc = None

        self.__pack()

    def pack_control(self, control: AMDTP_CONTROL, serial_number: int):
        """
        Packs the control information into the AMDTPPacket for transmission.

        Args:
            control (AMDTP_CONTROL): The control information.
            serial_number (int): Serial number.

        """
        self.length = 1 + 1 + self.CRC_SIZE
        self.header_ack = 0
        self.header_encrypted = 0
        self.header_sn = 0
        self.header_type = AMDTP_PKT_TYPE.CONTROL
        self.data = [control, serial_number]
        self.crc = None

        self.__pack()


class BLESerial:

    def __init__(self, mac_address: str, timeout: float = 10.0) -> None:
        """
        Initialize the BLESerial instance.

        Args:
            mac_address (str): MAC address of the Bluetooth device.
            timeout (float, optional): Timeout value for various operations. Defaults to 10 seconds.

        Attributes:
            mac_address (str): MAC address of the Bluetooth device.
            timeout (float): Timeout value for various operations.
            timeout_packet (float): Max time to wait for a data packet write acknowledgment.
            log_enabled (bool): Flag indicating whether logging is enabled.
            client: BleakClient instance for communication with the Bluetooth device.
            is_connected (bool): Flag indicating whether a connection is established.

            write_lock (asyncio.Lock): Lock for ensuring thread safety during write operations.
            write_sn (int): Sequence number for write operations.
            write_packet: Data packet to be written.

            read_buffer_queue (queue.Queue): Queue for storing received data packets.
            read_buffer_byte (bytearray()): Bytearray to store the data in form of bytearray which is in read_buffer_queue
            read_sn (int): Sequence number for received data packets.

            ack_buffer_queue (asyncio.Queue): Asyncio Queue for storing acknowledgment/control packets.

            char_write: Characteristics for writing data to the Bluetooth device.
            char_read: Characteristics for reading data from the Bluetooth device.
            char_read_cccd: Client Characteristic Configuration Descriptor for read characteristics.
            char_ack: Characteristics for acknowledgment/control communication.
            char_ack_cccd: Client Characteristic Configuration Descriptor for acknowledgment/control characteristics.

            executor: ThreadPoolExecutor for executing tasks in a separate thread pool.
            loop: Asyncio event loop for managing asynchronous operations.
            future: Future object for tracking the asynchronous BLE communication task.
        """
        self.mac_address = mac_address
        self.timeout = timeout
        self.timeout_packet = 0.5
        self.log_enabled = False
        self.client = None
        self.is_connected = False

        self.write_lock = asyncio.Lock()
        self.write_sn = 0
        self.write_packet = None

        self.read_buffer_queue = queue.Queue()
        self.read_buffer_byte = bytearray()
        self.read_sn = -1

        self.ack_buffer_queue = asyncio.Queue()

        self.char_write = None
        self.char_read = None
        self.char_read_cccd = None
        self.char_ack = None
        self.char_ack_cccd = None

        self.loop = None
        self.thread = threading.Thread(target=self.__create_loop)
        self.thread.daemon = True
        self.thread_ready = threading.Event()
        self.thread.start()
        assert(self.thread_ready.wait(timeout=self.timeout))
        

        atexit.register(self.close)

    def open(self):
        """
        Open the BLESerial instance, creating a thread and establishing communication.
        """

        # Call the __establish_communication method using the created event loop
        communication = asyncio.run_coroutine_threadsafe(self.__establish_communication(), self.loop)
        communication.result()

    def __create_loop(self):
        """
        Create a new event loop and run forever. Meant to be run in thread.
        """
        # Create a new event loop
        self.loop = asyncio.new_event_loop()

        # Set the newly created loop as the current loop
        asyncio.set_event_loop(self.loop)

        self.thread_ready.set()
        # Run the event loop indefinitely
        self.loop.run_forever()

    async def __establish_communication(self):
        """
        Establish communication with the BLE device.

        This method performs the following steps:
        1. Discovers the BLE device
        2. Connects to the BLE device.
        2. Displays server information and the MTU size.
        3. Enables notifications for read and acknowledgment/control characteristics.
        """
        # Discover and connect to the BLE device
        ble_device = await self.__discover()

        # Connect to the discovered BLE device
        await self.__connect(device=ble_device)

        # Display server information and MTU size
        await self.server_info()
        print(f"MTU size: {self.client.mtu_size}")

        # Enable notifications for read and acknowledgment/control characteristics
        await self.__enable_notifications()

    async def __discover(self):
        """
        Discover the BLE device with the specified MAC address.

        Uses BleakScanner to find a device by its MAC address.
        If the device is found, it prints a message and returns the device object.

        Raises:
            BleakError: If no device with the specified MAC address is found within the timeout.

        Returns:
            BleakDevice: The discovered BLE device.

        """
        # Find the BLE device by its MAC address using BleakScanner
        device = await BleakScanner.find_device_by_address(self.mac_address, timeout=self.timeout)

        # Check if a device is found
        if device is None:
            # Raise an error if no device is found within the specified timeout
            raise BleakError(f"No device with MAC address {self.mac_address} found after {self.timeout} seconds.")

        # Check if the found device has the expected MAC address
        if device.address == self.mac_address:
            # Print a message indicating that the device is found
            print(f"Device with MAC address {self.mac_address} found!")

        # Return the discovered BLE device
        return device

    async def __connect(self, device):
        """
        Connect to the specified BLE device.

        This asynchronous function creates a BleakClient instance, connects to the device,
        and updates the connection status.

        Args:
            device (BleakDevice): The BLE device to connect to.

        Raises:
            BleakError: If unable to create a client instance or connect to the device.

        """
        
        # If use_cached_services = True
        # Can improve performance and reduce discovery time,
        # But may lead to stale service information in dynamic environments and Potential Connection Issues
        # In our case we are using False, since it was causing frequent connection issue with True

        # Create a BleakClient instance for the specified device
        self.client = BleakClient(device, timeout=self.timeout)
        # self.client = BleakClient(device, timeout=self.timeout, winrt={"use_cached_services": False}) # meant to be used when BLE services are changing or being developed

        # Check if the client instance is successfully created
        if self.client is None:
            raise BleakError(
                f"Unable to get client info for the device with MAC address {self.mac_address} within {self.timeout} seconds."
            )

        # Connect to the BLE device
        await self.client.connect()

        # Update the connection status based on the client's connection status
        self.is_connected = self.client.is_connected

        # Check if the connection is successful
        if self.is_connected:
            print(f"Connected to the device with MAC address {self.mac_address}")
        else:
            # Raise an error if unable to connect to the specified device
            raise BleakError(f"Unable to connect to the device with MAC address {self.mac_address}")

    async def server_info(self):
        """
        Display information about the connected BLE server's services, characteristics, and descriptors.

        This function prints information about the services, characteristics, and descriptors of the connected BLE server.
        It also sets internal attributes based on characteristic handles for later use.

        Note:
            This function assumes specific characteristic handles (e.g., CHAR_WRITE, CHAR_READ, CHAR_ACK).

        Prints:
            Services and their characteristics with associated properties.
            Descriptors of each characteristic.

        Sets:
            - char_write: Characteristic for writing data.
            - char_read: Characteristic for reading data.
            - char_ack: Characteristic for acknowledgment/control.

            - char_read_cccd: Descriptor for read characteristic Client Characteristic Configuration.
            - char_ack_cccd: Descriptor for acknowledgment/control characteristic Client Characteristic Configuration.
        """
        print("----------Services----------")

        # Get the list of services from the BLE client
        svcs = self.client.services

        # Iterate through each service
        for service in svcs:
            self.packet_log(f"Service: {service}")

            # Iterate through characteristics of the service
            for char in service.characteristics:
                self.packet_log(f"  Characteristic: {char}")
                self.packet_log(f"    Properties: {char.properties}")

                # Match characteristic handle to set internal attributes
                match char.handle:
                    case AMDTP_CHAR_HANDLE.WRITE:
                        self.char_write = char
                    case AMDTP_CHAR_HANDLE.READ:
                        self.char_read = char
                    case AMDTP_CHAR_HANDLE.ACK:
                        self.char_ack = char

                # Iterate through descriptors of the characteristic
                for desc in char.descriptors:
                    self.packet_log(f"    Descriptor: {desc}")

                    # Match descriptor handle to set internal attributes
                    match desc.handle:
                        case AMDTP_CHAR_HANDLE.READ_CCCD:
                            self.char_read_cccd = desc
                        case AMDTP_CHAR_HANDLE.ACK_CCCD:
                            self.char_ack_cccd = desc

    async def __enable_notifications(self):
        """
        Enable notifications for read and acknowledgment/control characteristics.

        This method starts notifications for the read and acknowledgment/control characteristics of the BLE device.
        It also prints status messages during the process.
        """
        # Start notifications for read and acknowledgment/control characteristics
        await self.client.start_notify(self.char_read, self.callback_read)
        await self.client.start_notify(self.char_ack, self.callback_ack)

        print("Notifications enabled, Callbacks started")

    async def callback_read(self, sender: BleakGATTCharacteristic, data: bytearray):
        """
        Callback function for handling received data packets.

        Args:
            sender (BleakGATTCharacteristic): The sender characteristic.
            data (bytearray): The received data.

        Raises:
            ValueError: If the header type is not recognized.
            NotImplementedError: If there is an unpack error in the received data packet.
            NotImplementedError: If the status in the acknowledgment packet is not handled.
        """
        # Log the received data packet
        self.packet_log(f'RX - {len(data)}: {data.hex(" ")}')

        # Initialize an AMDTPPacket for processing the received data
        packet = AMDTPPacket()

        # Initialize an acknowledgment packet
        ack_packet = AMDTPPacket()

        # Unpack the received data and check for errors
        status = packet.unpack(data)
        if packet.header_type != AMDTP_PKT_TYPE.DATA:
            raise ValueError(f"callback_read {packet.header_type}")  # Unexpected header type

        # Process based on the status of the received data packet
        match status:
            case AMDTP_STATUS.SUCCESS:
                self.read_buffer_queue.put(packet.data)
                self.read_sn = packet.header_sn
            case AMDTP_STATUS.CRC_ERROR:
                pass  # no additional action
            case AMDTP_STATUS.INSUFFICIENT_BUFFER:
                raise NotImplementedError(
                    "AMDTP_STATUS.INSUFFICIENT_BUFFER, update unpack to generate this error if needed"
                )
            case AMDTP_STATUS.INVALID_PKT_LENGTH:
                pass  # no additional action
            case _:
                raise NotImplementedError(f"{AMDTP_STATUS(packet.data[0])}")

        # Create an acknowledgment packet and send it
        ack_packet.pack_ack(status)
        await self.__write_packet_ackctrl(ack_packet)

    async def callback_ack(self, sender: BleakGATTCharacteristic, data: bytearray):
        """
        Callback function for handling received acknowledgment and control packets.

        Args:
            sender (BleakGATTCharacteristic): The sender characteristic.
            data (bytearray): The received data.

        Raises:
            NotImplementedError: If there is an unpack error in the acknowledgment packet.
            NotImplementedError: If the status in the acknowledgment packet is not handled.
            ValueError: If the header type is not recognized.
        """
        # Log the received acknowledgment/control packet
        self.packet_log(f'RX ACK/CTRL - {len(data)}: {data.hex(" ")}')

        # Initialize an AMDTPPacket for processing the received data
        packet = AMDTPPacket()

        # Unpack the received data and check for errors
        unpack_status = packet.unpack(data)
        if unpack_status != AMDTP_STATUS.SUCCESS:
            raise NotImplementedError("ACK unpack error, not sure how to handle this")

        # Process based on the header type of the packet
        if packet.header_type == AMDTP_PKT_TYPE.ACK:
            
            # This will be used in __write_packet function 
            await self.ack_buffer_queue.put(packet.data[0])

        elif packet.header_type == AMDTP_PKT_TYPE.CONTROL:
            serial_number = packet.data[1]
            match AMDTP_CONTROL(packet.data[0]):
                case AMDTP_CONTROL.RESEND_REQ:
                    response = AMDTPPacket()
                    if serial_number != self.read_sn:
                        response.pack_ack(AMDTP_STATUS.RESEND_REPLY)
                        await self.__write_packet_ackctrl(response)
                    else:
                        response.pack_ack(AMDTP_STATUS.SUCCESS)
                        await self.__write_packet_ackctrl(response)
                case _:
                    raise ValueError("Not other control packet types")
        else:
            raise ValueError(f"Unrecognized header type: {packet.header_type}")

    async def __write_packet_data(self, packet: AMDTPPacket):
        """
        Writes a data packet to the BLE device.

        Args:
            packet (AMDTPPacket): The AMDTPPacket containing data.

        Raises:
            ValueError: If the packet length is invalid.
        """
        # Check if the packet length is valid
        if len(packet.raw) < (AMDTPPacket.DATA_LEN_SIZE + AMDTPPacket.HEADER_SIZE + AMDTPPacket.CRC_SIZE):
            raise ValueError("Invalid packet length")

        # Write the packet to the BLE device
        await self.client.write_gatt_char(self.char_write, packet.raw)

        # Log the transmitted data packet
        self.packet_log(f'TX - {len(packet.raw)}: {packet.raw.hex(" ")}')

    async def __write_packet_ackctrl(self, packet: AMDTPPacket):
        """
        Writes an acknowledgment/control packet to the BLE device.

        Args:
            packet (AMDTPPacket): The AMDTPPacket containing acknowledgment or control data.

        Raises:
            ValueError: If the packet length is invalid.
        """
        # Check if the packet length is valid
        if len(packet.raw) < (AMDTPPacket.DATA_LEN_SIZE + AMDTPPacket.HEADER_SIZE + AMDTPPacket.CRC_SIZE):
            raise ValueError("Invalid packet length")

        # Write the packet to the BLE device
        await self.client.write_gatt_char(self.char_ack, packet.raw)

        # Log the transmitted acknowledgment/control packet
        self.packet_log(f'TX ACK/CTRL - {len(packet.raw)}: {packet.raw.hex(" ")}')

    async def __write_packet(self, data: bytearray | list[int]):
        """
        Writes a packetized data to the BLE device.

        Args:
            data (bytearray or list[int]): The data to be written in the packet.

        Returns:
            int: The number of bytes sent.
        """
        # Acquire the write lock to ensure thread safety
        await self.write_lock.acquire()

        # Calculate the maximum data size based on the client MTU size
        max_data_size = self.client.mtu_size - 11  # 11 is a constant offset

        # Create a new AMDTPPacket instance
        self.write_packet = AMDTPPacket()

        # Initialize variables for tracking the progress of sending data
        sent = 0
        start_time = time.time()

        # Continue sending data until all bytes are sent or a timeout occurs
        while sent < len(data) and not self.__timeout(start_time):
            # Determine the size of the current packet to be sent
            size = min(max_data_size, len(data) - sent)

            # Pack the data into the AMDTP packet
            self.write_packet.pack_data(data[sent : sent + size], self.write_sn)

            # Write the AMDTP packet data to the BLE device
            await self.__write_packet_data(self.write_packet)

            while not self.__timeout(start_time):
                try:
                    # Wait for acknowledgment from the BLE device
                    write_ack = await asyncio.wait_for(self.ack_buffer_queue.get(), self.timeout_packet)

                    # Process the acknowledgment based on the status
                    match AMDTP_STATUS(write_ack):
                        case AMDTP_STATUS.SUCCESS:
                            self.write_sn = (self.write_sn + 1) % 16
                            break
                        case AMDTP_STATUS.CRC_ERROR, AMDTP_STATUS.INVALID_PKT_LENGTH, AMDTP_STATUS.RESEND_REPLY:
                            await self.__write_packet_data(self.write_packet)
                            continue
                        case AMDTP_STATUS.INSUFFICIENT_BUFFER:
                            raise NotImplementedError("AMDTP_STATUS.INSUFFICIENT_BUFFER, not sure how to handle this")
                        case _:
                            raise NotImplementedError(f"{AMDTP_STATUS(write_ack)}")
                    
                except asyncio.exceptions.TimeoutError:
                    # Handle timeout by attempting to resend the packet
                    # Create a control packet for requesting resend
                    resend = AMDTPPacket()
                    resend.pack_control(AMDTP_CONTROL.RESEND_REQ, self.write_packet.header_sn)
                    await self.__write_packet_ackctrl(resend)
                    continue

            # Update the total number of bytes sent
            sent += size

        # Release the write lock
        self.write_lock.release()

        return sent

    def write(self, data: bytearray | list[int], blocking: bool = True) -> None:
        """
        Writes data to the BLE device.

        Args:
            data (bytearray or list[int]): The data to be written.
            blocking (bool, optional): If True, the method will block until the write operation is complete.
                                       If False, it will initiate the write operation and return immediately.
                                       Defaults to True.

        Returns:
            None

        Note:
            This method relies on the presence of the __write_packet method and the event loop (self.loop).

        """
        # Run the __write_packet method asynchronously using the event loop
        write = asyncio.run_coroutine_threadsafe(self.__write_packet(data), self.loop)

        # If blocking, wait for the result of the write operation
        if blocking:
            write.result()

    # follows interface of pyserial in_waiting
    @property
    def in_waiting(self):
        while not self.read_buffer_queue.empty():
            self.read_buffer_byte.extend(self.read_buffer_queue.get())
        return len(self.read_buffer_byte)
    
    # follows interface of pyserial
    def reset_input_buffer(self):
        if self.in_waiting:
            self.read_buffer_byte.clear()
        
    def read(self, size: int) -> bytearray:
        """
        Read Method with Size Constraint

        This method reads a specified size of data from the read buffer queue. It aims to fulfill the requested size by
        concatenating data from the queue until the desired size is reached or a timeout occurs.

        Parameters:
        - size (int): The requested size of data to be read.

        Returns:
        - bytearray: The read data with a size up to the requested size.

        """
        # Return an empty bytearray if an invalid size is provided
        if size <= 0:
            return bytearray()
        
        # Concatenate data from the queue until it is empty
        while not self.read_buffer_queue.empty():
            self.read_buffer_byte.extend(self.read_buffer_queue.get())

        # Record the start time for timeout tracking
        start_time = time.time()

        # Keep waiting for data until the requested size is reached or a timeout occurs
        while size > len(self.read_buffer_byte) and not self.__timeout(start_time):
            # This operation waits for a short duration (timeout=0.005) to allow data to be added to the queue
            try:
                self.read_buffer_byte.extend(self.read_buffer_queue.get(block=True, timeout=0.005))
            except Exception:
                # Exception is caught if the queue is empty during the specified timeout
                pass

        # Determine the available data for reading
        read_available = min(size, len(self.read_buffer_byte))

        # Extract the available data from the byte buffer
        if read_available > 0:
            output = self.read_buffer_byte[:read_available]
            self.read_buffer_byte = self.read_buffer_byte[read_available:]
            return output
        
        return bytearray()

    def __timeout(self, start_time: float):
        """
        Checks if the timeout period has elapsed.

        Args:
            start_time (float): The starting time of the operation.

        Returns:
            bool: True if the timeout period has elapsed, False otherwise.
        """
        # Calculate the elapsed time since the operation started
        elapsed_time = time.time() - start_time

        # Check if the elapsed time exceeds the specified timeout
        return elapsed_time >= self.timeout

    def packet_log(self, log: str):
        """
        Logs the provided message if logging is enabled.

        Args:
            log (str): The message to be logged.
        """
        # Check if logging is enabled
        if self.log_enabled:
            # Print the log message
            print(log)

    async def __disable_notifications(self):
        """
        Disable notifications for read and acknowledgment/control characteristics.

        This asynchronous method uses the BleakClient's stop_notify method to halt notifications
        for the specified characteristics (char_read and char_ack). It also stops the corresponding callback functions.
        A message is printed indicating that notifications are disabled, and callbacks are stopped.

        Note:
            This function relies on the presence of BleakClient instance (self.client), and
            characteristic instances (self.char_read, self.char_ack), and callback functions (self.callback_read, self.callback_ack).

        """
        # Stop notifications for read and acknowledgment/control characteristics
        await self.client.stop_notify(self.char_read)
        await self.client.stop_notify(self.char_ack)

        print("Notifications disabled, Callbacks stopped")

    async def __disconnect(self):
        """
        Disconnect from the Bluetooth device.

        If a client is available, this asynchronous function first disables notifications using __disable_notifications(),
        then disconnects from the device, and finally prints "Disconnected from the device."

        Note:
            This function relies on the presence of a BleakClient instance (self.client).

        Raises:
            asyncio.TimeoutError: If the disconnection process takes longer than the specified timeout.

        """
        if self.client and self.client.is_connected:
            # Disable notifications before disconnecting
            await self.__disable_notifications()

            # Disconnect from the Bluetooth device with a timeout
            await asyncio.wait_for(self.client.disconnect(), timeout=self.timeout)

            # Update the connection status
            self.is_connected = False

            print("Disconnected from the device.")

    def close(self):
        """
        Closes the BLESerial instance.

        This method performs the following steps:
        1. Disconnects from the BLE device asynchronously.
        2. Safely stops the event loop if running.
        3. Shuts down the thread pool executor.

        Note:
            This method relies on the presence of attributes: loop, future, and executor.

        Warning:
            The executor shutdown is performed with wait=False and cancel_futures=True, indicating
            that the method does not wait for pending tasks to complete and cancels any pending tasks.

        Raises:
            Exception: An error occurred during disconnection or shutdown.
        """
        # Check if the event loop is available and running
        if self.loop is not None:
            if self.loop.is_running():
                try:
                    # Disconnect from the BLE device
                    disconnect = asyncio.run_coroutine_threadsafe(self.__disconnect(), self.loop)
                    disconnect.result(timeout=self.timeout)
                except Exception as e:
                    print(e)
                self.loop.call_soon_threadsafe(self.loop.stop)
                while self.loop.is_running():
                    pass

            self.loop.call_soon_threadsafe(self.loop.close)


if __name__ == "__main__":
    pass


# Example usage:
# ble_serial = BLESerial(mac_address="00:11:22:33:44:55")
# ble_serial.open()
# ble_serial.write(bytearray(b"Hello, BLE!"))
# my_data = ble_serial.read(5)
# print(my_data)
# ble_serial.close()

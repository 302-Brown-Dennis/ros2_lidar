import rclpy
import rclpy
from rclpy.node import Node
import serial
import math
from sensor_msgs.msg import LaserScan


# Creating class for lidar messages
class LidarMessage:
    def __init__(self, header, verlen, speed, start_angle, end_angle, timestamp, crc):
        self.header = header
        self.verlen = verlen
        self.speed = speed
        self.start_angle = start_angle
        self.data = []
        self.intensity_data = []
        self.end_angle = end_angle
        self.timestamp = timestamp
        self.crc = crc

serial_port = "COM4"
baud_rate = 230400
ser = serial.Serial(serial_port, baud_rate, timeout=1, bytesize=8, parity='N', stopbits=1)

def read_message(ser):
    message = b''
    header_found = False

    while True:
        data = ser.read(1)
        if data == b'\x54':
            if header_found:
                if len(message) >= 14:
                    return message
                else:
                    message = b'' # reset if incomplete
            else:
                header_found = True
                message += data
                continue
        if header_found:
            message += data

CrcTable = [
    0x00, 0x4d, 0x9a, 0xd7, 0x79, 0x34, 0xe3, 0xae, 0xf2, 0xbf, 0x68, 0x25, 0x8b, 0xc6, 0x11, 0x5c, 
    0xa9, 0xe4, 0x33, 0x7e, 0xd0, 0x9d, 0x4a, 0x07, 0x5b, 0x16, 0xc1, 0x8c, 0x22, 0x6f, 0xb8, 0xf5, 
    0x1f, 0x52, 0x85, 0xc8, 0x66, 0x2b, 0xfc, 0xb1, 0xed, 0xa0, 0x77, 0x3a, 0x94, 0xd9, 0x0e, 0x43, 
    0xb6, 0xfb, 0x2c, 0x61, 0xcf, 0x82, 0x55, 0x18, 0x44, 0x09, 0xde, 0x93, 0x3d, 0x70, 0xa7, 0xea, 
    0x3e, 0x73, 0xa4, 0xe9, 0x47, 0x0a, 0xdd, 0x90, 0xcc, 0x81, 0x56, 0x1b, 0xb5, 0xf8, 0x2f, 0x62, 
    0x97, 0xda, 0x0d, 0x40, 0xee, 0xa3, 0x74, 0x39, 0x65, 0x28, 0xff, 0xb2, 0x1c, 0x51, 0x86, 0xcb, 
    0x21, 0x6c, 0xbb, 0xf6, 0x58, 0x15, 0xc2, 0x8f, 0xd3, 0x9e, 0x49, 0x04, 0xaa, 0xe7, 0x30, 0x7d, 
    0x88, 0xc5, 0x12, 0x5f, 0xf1, 0xbc, 0x6b, 0x26, 0x7a, 0x37, 0xe0, 0xad, 0x03, 0x4e, 0x99, 0xd4, 
    0x7c, 0x31, 0xe6, 0xab, 0x05, 0x48, 0x9f, 0xd2, 0x8e, 0xc3, 0x14, 0x59, 0xf7, 0xba, 0x6d, 0x20, 
    0xd5, 0x98, 0x4f, 0x02, 0xac, 0xe1, 0x36, 0x7b, 0x27, 0x6a, 0xbd, 0xf0, 0x5e, 0x13, 0xc4, 0x89, 
    0x63, 0x2e, 0xf9, 0xb4, 0x1a, 0x57, 0x80, 0xcd, 0x91, 0xdc, 0x0b, 0x46, 0xe8, 0xa5, 0x72, 0x3f, 
    0xca, 0x87, 0x50, 0x1d, 0xb3, 0xfe, 0x29, 0x64, 0x38, 0x75, 0xa2, 0xef, 0x41, 0x0c, 0xdb, 0x96, 
    0x42, 0x0f, 0xd8, 0x95, 0x3b, 0x76, 0xa1, 0xec, 0xb0, 0xfd, 0x2a, 0x67, 0xc9, 0x84, 0x53, 0x1e, 
    0xeb, 0xa6, 0x71, 0x3c, 0x92, 0xdf, 0x08, 0x45, 0x19, 0x54, 0x83, 0xce, 0x60, 0x2d, 0xfa, 0xb7, 
    0x5d, 0x10, 0xc7, 0x8a, 0x24, 0x69, 0xbe, 0xf3, 0xaf, 0xe2, 0x35, 0x78, 0xd6, 0x9b, 0x4c, 0x01, 
    0xf4, 0xb9, 0x6e, 0x23, 0x8d, 0xc0, 0x17, 0x5a, 0x06, 0x4b, 0x9c, 0xd1, 0x7f, 0x32, 0xe5, 0xa8
]

# New CRC function based on provided implementation
def cal_crc8(p, length):
    crc = 0
    for i in range(length):
        crc = CrcTable[(crc ^ p[i]) & 0xff]
    return crc

def convert_message_lidar(message: bytes):
    length = len(message)
    if length < 14:
        return None

    m1 = LidarMessage(
        header=message[0],
        verlen=message[1],
        speed=int.from_bytes(message[2:4], 'little'),
        start_angle=int.from_bytes(message[4:6], 'little'),
        end_angle=int.from_bytes(message[-5:-3], 'little'),
        timestamp=int.from_bytes(message[-3:-1], 'little'),
        crc=message[-1]
    )

    m1.data = []
    m1.intensity_data = []
    for i in range(6, length - 8, 3):
        m1.data.append(int.from_bytes(message[i: i+2], 'little'))
        m1.intensity_data.append(message[i+3]) # for intensity
    
    #calculated_crc = cal_crc8(message, len(message) - 1)
    #print(f"Calculated CRC: {calculated_crc}, Actual CRC: {m1.crc}")
    
    #calculate crc and check it
    if m1.crc == cal_crc8(message, len(message) - 1): # len - 1 so it doesn't include the crc byte itself
        return m1

    else: 
        return None

class SendLaserMsgNode(Node):
    def __init__(self):
        super.__init__("send_laser")
        self.publisher_ = self.create_publisher(LaserScan, "scan2", 10)
        self.get_logger().info("Send Laser Message Node has been started!")
    
    def send_msg(self):
        msg = LaserScan()
        ser_msg = read_message(ser)
        con_msg = convert_message_lidar(ser_msg)
        if con_msg is not None:
            msg.angle_min = math.radians(con_msg.start_angle / 100)
            msg.angle_max = math.radians(con_msg.end_angle / 100)
            if con_msg.end_angle < con_msg.start_angle:
                con_msg.end_angle += 36000
            msg.angle_increment = math.radians((con_msg.end_angle - con_msg.start_angle) / 100 / len(con_msg.data))
            msg.ranges = [x / 1000 for x in con_msg.data]
            msg.range_min = min(msg.ranges)
            msg.range_max = max(msg.ranges)
            msg.intensities = con_msg.intensity_data

            self.publisher_.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = SendLaserMsgNode()
    rclpy.spin(node)
    rclpy.shutdown()
    ser.close()

if __name__ == '__main__':
    main()

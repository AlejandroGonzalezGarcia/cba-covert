import serial
import struct
import string
import random
import numpy as np
from pylsl import StreamInfo, StreamOutlet
from serial.tools import list_ports

# TODO: LOOK AT BLUETOOTH PORTS, PROMPT USER TO SELECT DEVICE, MAKE GENERALIZABLE ACROSS OS PLATFORMS
# device='/dev/cu.UN-20220329'
device = "/dev/rfcomm0"


blocksize=0.2
timeout=5 # define time required before software times out
nchan=16 # 16 channels total (8 EEG, 3 accel, 3 gyro, battery, counter)
fsample=250 # sampling rate

# CONTROL COMMANDS
start_acq      = [0x61, 0x7C, 0x87] # send these 3 bytes to unicorn to start streaming EEG data
stop_acq       = [0x63, 0x5C, 0xC5] # send these 3 bytes to unicorn to stop streaming data
start_response = [0x00, 0x00, 0x00] # device replies with these 3 bytes to indicate streaming has started
stop_response  = [0x00, 0x00, 0x00] # device sends these 3 bytes to indicate streaming has stopped

# PACKET FREAMING MARKERS
start_sequence = [0xC0, 0x00] # the beginning 2 bytes of a packet length  
stop_sequence  = [0x0D, 0x0A] # the ending 2 bytes of a packet length

# MAIN IDEA:
# 2 BYTES (START), 41 BYTES (PAYLOAD), 2 BYTES (STOP) = 45 BYTES TOTAL BEING SENT AT 250 HZ
# EEG 24-BIT VALUES ARE STORED IN 3 BYTES AND ARE BIG ENDIAN
# ACCEL AND GYRO VALUES ARE STORED IN 2 BYTES EACH (4 TOTAL) AND ARE LITTLE ENDIAN
# COUNTER IS 4 BYTES (MUST NOT OVERFLOW) AND IS LITTLE ENDIAN
# BATTERY IS 1 BYTE

# try:
#     s = serial.Serial(device, 115200, timeout=timeout) # open serial port and set baud rate to 115200
#     print("connected to serial port " + device)
# except:
#     raise RuntimeError("cannot connect to serial port " + device) # error if there is no port with that device

# function to check for and open port if it exists
def open_serial_port(device, baudrate=115200, timeout=timeout):
    try:
        s = serial.Serial(port=device,
                          baudrate=baudrate,
                          timeout=timeout)
        
        if not s.is_open:
            raise RuntimeError(f"Port {device} did not open")
        
        s.reset_input_buffer()
        s.reset_output_buffer()

        print(f"Connected to serial port: {device}")
        return s
    except serial.SerialException as e:
        raise RuntimeError(f"Cannot connect to serial port {device}: {e}")

s = open_serial_port(device) # check for port and open it if it exists

# define parameters for LSL
lsl_name    = 'Unicorn' # how it will appear in LSL viewers
lsl_type    = 'EEG' # helps filter streams
lsl_format  = 'float32' # each channel value is a 32-bit floating point 
lsl_id      = ''.join(random.choice(string.digits) for i in range(6)) # random 6-digit ID for thre stream
                  
# create an outlet stream
info = StreamInfo(lsl_name, lsl_type, nchan, fsample, lsl_format, lsl_id) # create stream info
outlet = StreamOutlet(info) # open LSL transmission socket using info defined above
# EACH SAMPLE PUSHED TO OUR OUTLET MUST BE A LIST OR ARRAY OF LENGTH NCHAN (16) AND OF TYPE FLOAT

print(info)
print('started LSL stream: name=%s, type=%s, id=%s' % (lsl_name, lsl_type, lsl_id))

# start the Unicorn data stream
print(f"Port open: {s.is_open}")
print("Sending start command...")
s.write(start_acq) # send 3 byte command according to the start sequence to tell the unicorn to start streaming
    
print("Waiting for response...")
response = s.read(3) # read 3 bytes from the serial port to see how the unicorn responds back to start command
if response != b'\x00\x00\x00': # repsonse must be 00 00 00 according to start response
    del outlet
    raise RuntimeError(f"Cannot start data stream. First 3 bytes received: {response}") # if response does not match start response trigger error

print('started Unicorn')

try:
    while True:
        dat = np.zeros(nchan) # define a data array to be of length equal to nchan (16)
        
        # read one block of data from the serial port
        payload = s.read(45) # 45 bytes total
        if len(payload) != 45: # make sure every packet we receive is 45 bytes
            raise RuntimeError(f"Incomplete packet: received {len(payload)} bytes instead of 45.")
        
        # check the start and end bytes
        if payload[0:2] != b'\xC0\x00': # make sure the start sequence is correct C0 00
            raise RuntimeError(f"Invalid start bytes: {payload[0:2]}") 
        if payload[43:45] != b'\x0D\x0A': # make sure end sequence is correct 0D 0A
            raise RuntimeError(f"Invalid end bytes: {payload[43:45]}")
    
        battery = 100*float(payload[2] & 0x0F)/15
    
        eeg = np.zeros(8) # define an array for EEG channels (8 channels)
        raw_eeg = np.zeros(8)
        # for ch in range(0,8): 
        #     # unpack as a big-endian 32 bit signed integer
        #     eegv = struct.unpack('>i', b'\x00' + payload[(3+ch*3):(6+ch*3)])[0]
        #     # apply two’s complement to the 32-bit signed integral value if the sign bit is set
        #     if (eegv & 0x00800000):   
        #         eegv = eegv | 0xFF000000
        #     eeg[ch] = float(eegv) * 4500000. / 50331642.

        for ch in range(8):
            b = payload[3 + ch*3 : 6 + ch*3]                 # 3 bytes
            v = int.from_bytes(b, byteorder="big", signed=False)  # 0..2^24-1
            if v & 0x800000:                                 # sign bit for 24-bit
                v -= 1 << 24                                 # now in [-2^23, 2^23-1]
            raw_eeg[ch] = v
            eeg[ch] = float(v) * 4500000.0 / 50331642.0  
    
        accel = np.zeros(3)
        # unpack as a little-endian 16 bit signed integer
        accel[0] = float(struct.unpack('<h', payload[27:29])[0]) / 4096.
        accel[1] = float(struct.unpack('<h', payload[29:31])[0]) / 4096.
        accel[2] = float(struct.unpack('<h', payload[31:33])[0]) / 4096.
    
        gyro = np.zeros(3)
        # unpack as a little-endian 16 bit signed integer
        gyro[0] = float(struct.unpack('<h', payload[33:35])[0]) / 32.8
        gyro[1] = float(struct.unpack('<h', payload[35:37])[0]) / 32.8
        gyro[2] = float(struct.unpack('<h', payload[37:39])[0]) / 32.8
    
        counter = struct.unpack('<L', payload[39:43])[0]
    
        # assign data to corresponding indices in data array
        dat[0:8]   = eeg
        dat[8:11]  = accel
        dat[11:14] = gyro
        dat[14]    = battery
        dat[15]    = counter
            
        # send the data to LSL
        outlet.push_sample(dat)

        if ((counter % fsample) == 0):
            print(f"3 bytes received from eeg: {payload[3 + 3 : 6 + 3]}")
            print('received %d samples, battery %d %%' % (counter, battery))

        if counter % 250 == 0:
            print(f"\nctr={counter}  batt={battery:.0f}%")
            print("raw24 EEG counts:", raw_eeg.tolist())
            print("EEG (scaled):    ", [f"{x:.2f}" for x in eeg])   # expect ~tens of uV (HAVE NOT TESTED)
            print("accel (g):       ", [f"{x:.3f}" for x in accel]) # one axis ~±1 when still
            print("gyro:            ", [f"{x:.2f}" for x in gyro])  # near 0 when still

except:
    print('closing')
    s.write(stop_acq)
    s.close()
    del outlet
    
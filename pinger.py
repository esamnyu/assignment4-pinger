from socket import socket, AF_INET, SOCK_RAW, IPPROTO_ICMP, error, htons
import socket
import os
import sys
import struct
import time
import select
import binascii
import pandas as pd
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

ICMP_ECHO_REQUEST = 8

def checksum(string):
    csum = 0
    countTo = (len(string) // 2) * 2
    count = 0

    while count < countTo:
        thisVal = (string[count + 1]) * 256 + (string[count])
        csum += thisVal
        csum &= 0xffffffff
        count += 2

    if countTo < len(string):
        csum += (string[len(string) - 1])
        csum &= 0xffffffff

    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer

def receiveOnePing(mySocket, ID, timeout, destAddr):
    timeLeft = timeout

    while 1:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        if whatReady[0] == []:  # Timeout
            return "Request timed out."

        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)

        # Extract the ICMP header from the IP packet
        icmpHeader = recPacket[20:28]
        icmpType, code, checksum, packetID, sequence = struct.unpack("bbHHh", icmpHeader)

        if packetID == ID:
            # Calculate the round-trip time (RTT) and time-to-live (TTL)
            rtt = (timeReceived - time.time()) * 1000
            ttl = struct.unpack("B", bytes([recPacket[8]]))[0]

            return "{},{},{}".format(packetID, round(rtt, 2), ttl)

        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return "Request timed out."

def sendOnePing(mySocket, destAddr, ID):
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)

    myChecksum = 0
    # Make a dummy header with a 0 checksum
    # struct -- Interpret strings as packed binary data
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    data = struct.pack("d", time.time())
    # Calculate the checksum on the data and the dummy header.
    myChecksum = checksum(header + data)

    # Get the right checksum, and put in the header

    if sys.platform == 'darwin':
        # Convert 16-bit integers from host to network  byte order
        myChecksum = htons(myChecksum) & 0xffff
    else:
        myChecksum = htons(myChecksum)


    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data

    mySocket.sendto(packet, (destAddr, 1))  # AF_INET address must be tuple, not str

    # Both LISTS and TUPLES consist of a number of objects
    # which can be referenced by their position number within the object.

def doOnePing(dest_addr, timeout, sequence_number=1):
    # Create ICMP packet
    ICMP_TYPE = 8
    ICMP_CODE = 0
    ICMP_CHECKSUM = 0
    ICMP_ID = 65535  # maximum value for an unsigned short int
    ICMP_SEQUENCE = sequence_number
    ICMP_PAYLOAD = b'Hello world'

    # Calculate ICMP checksum
    checksum = 0
    packet = struct.pack("!BBHHH6s", ICMP_TYPE, ICMP_CODE, ICMP_CHECKSUM, ICMP_ID, ICMP_SEQUENCE, ICMP_PAYLOAD)
    for i in range(0, len(packet), 2):
        checksum += (packet[i] << 8) + packet[i+1]
    checksum = (checksum >> 16) + (checksum & 0xffff)
    checksum = ~checksum & 0xffff
    packet = struct.pack("!BBHHH6s", ICMP_TYPE, ICMP_CODE, checksum, ICMP_ID, ICMP_SEQUENCE, ICMP_PAYLOAD)

    # Create socket and set timeout
    icmp = socket.getprotobyname("icmp")
    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
    sock.settimeout(timeout)

    # Send ICMP packet
    send_time = time.time()
    sock.sendto(packet, (dest_addr, 0))

    # Receive ICMP packet
    try:
        data, addr = sock.recvfrom(1024)
        recv_time = time.time()
        time_diff = recv_time - send_time
        ip_header = data[:20]
        iph = struct.unpack('!BBHHHBBH4s4s' , ip_header)
        ttl = iph[5]
        saddr = socket.inet_ntoa(iph[8])
        return time_diff, ttl, saddr
    except socket.timeout:
        return None
    
def ping(host, timeout=1):
    destAddr = socket.gethostbyname(host)
    print("Pinging " + destAddr + " using Python:")
    print("")
    # Send ping requests to a server separated by approximately one second
    counter = 0  # Initialize a counter variable
    while counter < 4:  # Exit the loop after 4 pings have been sent
        # Create ICMP socket
        icmp = socket.getprotobyname("icmp")
        mySocket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
        myID = os.getpid() & 0xFFFF  # Generate a random ICMP packet ID

        # Send ICMP packet
        sendOnePing(mySocket, destAddr, myID)

        # Receive ICMP packet
        data = receiveOnePing(mySocket, myID, timeout, destAddr)

        # Close ICMP socket
        mySocket.close()

        # Print the received data
        if data == "Request timed out.":
            print(data)
        else:
            packetID, rtt, ttl = data.split(",")
            print("Reply from {}: bytes=32 time={}ms TTL={}".format(destAddr, rtt, ttl))

        time.sleep(1)  # Wait approximately one second before sending the next ping request
        counter += 1  # Increment the counter variable



if __name__ == '__main__':
    ping("google.com")

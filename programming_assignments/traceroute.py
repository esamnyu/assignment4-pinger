from socket import *
import os
import sys
import struct
import time
import select
import binascii
import pandas as pd

ICMP_ECHO_REQUEST = 8
MAX_HOPS = 60
TIMEOUT = 2.0
TRIES = 1
# The packet that we shall send to each router along the path is the ICMP echo
# request packet, which is exactly what we had used in the ICMP ping exercise.
# We shall use the same packet that we built in the Ping exercise

def checksum(string):
# In this function we make the checksum of our packet
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

def build_packet():
    ID = os.getpid() & 0xFFFF
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, 0, ID, 1)
    data = struct.pack("d", time.time())

    # Calculate the checksum and update the header
    my_checksum = checksum(header + data)
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, socket.htons(my_checksum), ID, 1)
    packet = header + data
    return packet

def get_route(hostname):
    timeLeft = TIMEOUT
    df = pd.DataFrame(columns=['Hop Count', 'Try', 'IP', 'Hostname', 'Response Code'])
    destAddr = gethostbyname(hostname)

    for ttl in range(1, MAX_HOPS):
        for tries in range(TRIES):
            # Create a raw socket
            mySocket = socket.socket(socket.AF_INET, socket.SOCK_RAW, IPPROTO_ICMP)
            mySocket.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, struct.pack('I', ttl))
            mySocket.settimeout(TIMEOUT)
            try:
                d = build_packet()
                mySocket.sendto(d, (hostname, 0))
                t = time.time()
                startedSelect = time.time()
                whatReady = select.select([mySocket], [], [], timeLeft)
                howLongInSelect = (time.time() - startedSelect)
                if whatReady[0] == []:  # Timeout
                    df = df.append({"Hop Count": ttl, "Try": tries + 1, "IP": None, "Hostname": None, "Response Code": "timeout"}, ignore_index=True)
                recvPacket, addr = mySocket.recvfrom(1024)
                timeReceived = time.time()
                timeLeft = timeLeft - howLongInSelect
                if timeLeft <= 0:
                    df = df.append({"Hop Count": ttl, "Try": tries + 1, "IP": None, "Hostname": None, "Response Code": "timeout"}, ignore_index=True)
            except Exception as e:
                continue
            else:
                # Extract ICMP header information
                icmp_header = recvPacket[20:28]
                types, code, checksum, packet_id, sequence = struct.unpack("bbHHh", icmp_header)
                
                # Get the hostname
                try:
                    host = socket.gethostbyaddr(addr[0])[0]
                except socket.herror:
                    host = "hostname not returnable"

                # Append data to the DataFrame
                df = df.append({"Hop Count": ttl, "Try": tries + 1, "IP": addr[0], "Hostname": host, "Response Code": types}, ignore_index=True)

                if types == 0:
                    return df
                break
    return df

if __name__ == '__main__':
    df = get_route("google.com")
    print(df)
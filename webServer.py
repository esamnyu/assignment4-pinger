# Import socket module
from socket import *
# Import sys module to terminate the program
import sys

def webServer(port=13331):
    # Create a TCP socket
    serverSocket = socket(AF_INET, SOCK_STREAM)
    
    # Bind the socket to a specific address and port
    serverSocket.bind(("", port))
    
    # Start listening for incoming connections
    serverSocket.listen(1)
    
    while True:
        # Accept an incoming connection
        print('Ready to serve...')
        connectionSocket, addr = serverSocket.accept()
        
        try:
            # Receive incoming message from client
            message = connectionSocket.recv(1024).decode()
            
            # Extract the requested file name from the message
            filename = message.split()[1]
            
            # Open the requested file
            with open(filename[1:], 'rb') as f:
                # Read the file content
                file_content = f.read()
                
                # Create the HTTP response header
                response_header = b"HTTP/1.1 200 OK\r\n" + \
                                  b"Content-Type: text/html; charset=UTF-8\r\n" + \
                                  b"Content-Length: " + str(len(file_content)).encode() + b"\r\n\r\n"
                
                # Send the HTTP response header and content to the client
                connectionSocket.sendall(response_header + file_content)
                
            # Close the connection socket
            connectionSocket.close()
        
        except Exception as e:
            # If the file was not found, send a 404 Not Found response to the client
            response_header = b"HTTP/1.1 404 Not Found\r\n\r\n"
            connectionSocket.sendall(response_header)
            connectionSocket.close()

if __name__ == "__main__":
    webServer(13331)

#!/usr/bin/env python3

# ===============================================================================
#              Log Reading and Forwarding Tool
#
# Requirement: "1. Log Reading Tool: Build a tool that reads logs from a file 
#              and sends them to a syslog server on a custom port."
#
# Description: This script reads log entries line-by-line from a specified
#              file and forwards them to a remote syslog server on a custom port.
#
# Written by:  Olesia Y.
# ===============================================================================

# ===============================================================================
# |              Some notes about sockets
# | 
# | A socket is an endpoint for sending or receiving data across a network.
# | In Python, 'socket' module wraps the OS-level network interface.
# | 
# |  Two main types are used here:
# |    1. TCP (SOCK_STREAM)
# |        - Connection-oriented.
# |        - Reliable: ensures all data arrives in order, resends if packets are lost.
# |        - Requires explicit framing to separate messages (syslog over TCP often
# |          uses "<length> message" format).
# | 
# |    2. UDP (SOCK_DGRAM)
# |       - Connectionless.
# |       - Faster, but unreliable: packets can be lost or arrive out of order.
# |       - No built-in framing - each 'sendto()' call is one discrete packet.
# | 
# | Common socket calls in this script:
# |    socket.socket(family, type)   -> Creating a socket (IPv4 + TCP/UDP type).
# |    sock.connect((host, port))    -> TCP-only: establishing a connection.
# |    sock.sendall(data)            -> TCP: sending all bytes, blocking until done.
# |    sock.sendto(data, addr)       -> UDP: send a datagram to the specific address.
# |    sock.close()                  -> Closing the socket.
# | 
# | Error handling:
# |    socket.error covers all network issues (timeout, connection reset, etc.).
# |    On TCP, losing connection raises an error - in that case, we reconnect.
# |    On UDP, errors usually occur only if the local OS refuses to send.
# | 
# | Link to a nice refresher material about sockets in Python - check here:
# | https://realpython.com/python-sockets/
# | 
# ===============================================================================

# ===============================================================================
# |              Some notes about "inode"
# |
# | In Unix-like file systems, every file has an *inode* (index node).
# | The inode stores metadata about the file (size, permissions, timestamps, etc.)
# | and uniquely identifies the file within its filesystem.
# | Two files can have the same name at different times, but they will have
# | different inode numbers because they are actually different files.
# |
# | Many logging systems use *log rotation* - periodically, the active log file
# | is renamed and replaced with a new empty file (often with the same name).
# | If we only tracked "last read byte offset" by file name, a rotated 
# | (renamed/recreated) file could trick the script into:
# |  - Skipping logs (if new file is smaller but we start from a big offset)
# |  - Re-reading old logs (if new file is bigger but unrelated to the old one)
# | By storing the inode together with the offset (inode:offset), we would know exactly which file
# | the offset refers to, even if the path stays the same.
# |
# | On each read, we would check the inode of LOG_FILE_PATH using 'os.stat(file_path).st_ino'.
# |  - This inode is converted to a string and used as the key in the state file.
# |  - If the inode changes (log rotated), our stored offset for the new inode
# |    will likely be missing - so we start reading from offset 0 for the new file.
# |
# | Benefits:
# |  - Prevents mixing offsets between different physical files.
# |  - Handles log rotation automatically without extra logic.
# |
# | Possible limitations:
# |  - If a file is rotated and replaced extremely quickly with the same inode,
# |    this method could misinterpret the file. This is rare in practice.
# | 
# | Problem with inode-only tracking:
# |   - Inode numbers are reused by the filesystem over time.
# |   - If we switch between different files (even with different names), they might eventually
# |     share the same inode number, especially if one file is deleted before another is created.
# |   - In an inode-only dictionary, this overwrites the old file's offset - we can only track
# |     one file at a time reliably.
# |
# | However, with "path + inode" approach, we store offsets keyed by: "<absolute_path>:<inode>".
# |   - This makes the key unique to both the physical file (inode) and its current path.
# |   - Benefits:
# |       1. Multiple files can be tracked independently in the same state file.
# |       2. Rotation for each file is still detected by inode changes.
# |       3. Switching between files won't lose offsets for others.
# | 
# ===============================================================================


# --- Standard Library Imports ---
# socket  : Provides low-level networking interface (TCP/UDP communication).
# os      : Interacts with the operating system (file metadata, path handling).
# json    : Reads/writes JSON (used here to store log reading position).
# time    : Provides sleep delays between iterations.
import socket
import os
import json
import time
# JSON was chosen here because it's human-readable, so the offsets can easily be seen in plain text. 
# Python's json module makes it easy to load and save without custom parsing code.

# --- Configuration ---
LOG_FILE_PATH="/home/azuregenerator/wh.log"
SYSLOG_SERVER_IP="10.0.0.5"
SYSLOG_SERVER_PORT=55141  # 55140 for UDP or 55141 for TCP
PROTOCOL="TCP"    # "UDP" or "TCP" - rsyslog server configuration supports both
STATE_FILE_PATH="/tmp/.log_sender_state.json" # Path to the JSON state file that stores the last read position
# Setting a delay in seconds between checking for new log lines in the log file.
# A small delay may prevent the script from consuming too much CPU.
POLLING_INTERVAL=2

# The function for getting the last read position from the state file (the last byte offset read from the log file, stored in STATE_FILE_PATH).
# Using a key of "absolute_path:inode" as a unique identifier to handle log rotation.
# This is to be able to read only the new logs instead of all the logs from the beginning every time the script starts to run. 
# If the log file is rotated (renamed/recreated), it will have a different inode. 
# This ensures we don't mistakenly use an offset from an old file version. 
# Multiple files can be tracked at once while still detecting log rotation for each file individually.
# This is an improvement in comparison with my first solution for the log reading tool using Bash.
def get_last_position(file_path, state_file):
    try:
        abs_path = os.path.abspath(file_path)
        inode = str(os.stat(file_path).st_ino)
        key = f"{abs_path}:{inode}"

        with open(state_file, 'r') as f:
            state = json.load(f)
            # Return the stored offset for this key, or 0 if not found.
            return state.get(key, 0)    # Returns integer offset in bytes, or defaults to 0 if no record exists
    except (FileNotFoundError, json.JSONDecodeError):
        # If the state file does not exist or is invalid, start from the beginning.
        return 0

# The function for writing the current read position (read byte offset) for the given file to the state file. 
# This ensures that in case the script restarts, it will resume where it previously left off. 
# Uses "absolute_path:inode" as the key so multiple files can coexist in state.
def update_last_position(file_path, state_file, offset):
    abs_path = os.path.abspath(file_path)
    inode = str(os.stat(file_path).st_ino)
    key = f"{abs_path}:{inode}"

    state = {}
    try:
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                state = json.load(f)
    except json.JSONDecodeError:
        # Exception - the file exists but is corrupted (invalid JSON), overwrite it.
        pass

    state[key] = offset
    with open(state_file, 'w') as f:
        json.dump(state, f)

# The function for sending a single log line to the syslog server
# Behavior:
#  - Strips newline characters.
#  - Skips empty lines.
#  - For UDP: sends datagram directly.
#  - For TCP: sends length-prefixed message (common syslog framing).
# Why TCP framing?
#  - Because syslog over TCP often expects a '<length> message' format to separate messages.
def send_log_message(sock, message, protocol):
    # Stripping any newlines and sending the message as a complete string.
    message = message.strip()
    if not message:
        return

    # Improvement in comparison to Bash script solution.
    # This way, there is no need to go through the whole script to modify all references to the protocol when switching between them.
    try:
        if protocol == "UDP":
            sock.sendto(message.encode('utf-8'), (SYSLOG_SERVER_IP, SYSLOG_SERVER_PORT))
            print(f"[PYTHON] Forwarding log over UDP: {message}")
        elif protocol == "TCP":
            message_bytes = message.encode('utf-8')
            framed_message = f"{len(message_bytes)} {message}".encode('utf-8')
            sock.sendall(framed_message)
            print(f"[PYTHON] Forwarding log over TCP: {message}")
    # Exception - raising socket.error if the connection fails. 
    except socket.error as e:
        print(f"Socket error: {e}. Attempting to reconnect...")
        raise


# Main function to initialize the socket and start the log-tailing loop.
# Improvement in comparison to the Bash solution, which just reads logs from the file and exits.
def main():
    # Creating the socket based on the chosen protocol
    if PROTOCOL == "UDP":
        sock_type = socket.SOCK_DGRAM
    elif PROTOCOL == "TCP":
        sock_type = socket.SOCK_STREAM
    else:
        print("Error: PROTOCOL must be 'TCP' or 'UDP'.")
        exit(1)

    print(f"Starting log sender to {SYSLOG_SERVER_IP}:{SYSLOG_SERVER_PORT} using {PROTOCOL}...")
    print(f" | Starting Python log sender script...\n")
    print(f" | --------------------------------------------------\n")
    print(f" | Source File:      {LOG_FILE_PATH}\n")
    print(f" | Destination Host: {SYSLOG_SERVER_IP}\n")
    print(f" | Destination Port: {SYSLOG_SERVER_PORT}\n")
    print(f" | Protocol: {PROTOCOL}\n")
    print(f" | --------------------------------------------------\n")

    while True:
        try:
            # Create a socket and connect if using TCP
            sock = socket.socket(socket.AF_INET, sock_type)
            if PROTOCOL == "TCP":
                sock.connect((SYSLOG_SERVER_IP, SYSLOG_SERVER_PORT))

            # Starting the "tailing" loop to continuously check for new logs in the file
            while True:
                # Getting the last known position. 
                # This call is outside of the file-opening block to ensure it is up to date on each loop iteration.
                last_pos = get_last_position(LOG_FILE_PATH, STATE_FILE_PATH)
                
                with open(LOG_FILE_PATH, 'r') as f:
                    f.seek(last_pos)
                    new_logs = f.readlines()
                    current_pos = f.tell()

                    if new_logs:
                        for line in new_logs:
                            send_log_message(sock, line, PROTOCOL)
                        # Writing the current read position to the state file
                        # We need to update the local last_pos variable with the new position to prevent re-reading the same logs on the next iteration.
                        update_last_position(LOG_FILE_PATH, STATE_FILE_PATH, current_pos)
                        last_pos = current_pos
                    
                time.sleep(POLLING_INTERVAL)

        except FileNotFoundError:
            print(f"Error: Log file cannot be found at {LOG_FILE_PATH}. Retrying in {POLLING_INTERVAL} seconds...")
            time.sleep(POLLING_INTERVAL)
        # Exception - if a socket error occurs (connection reset), close the socket and let the outer loop try to re-establish a connection.
        except socket.error as e:
            print(f"Socket error: {e}. Retrying connection in {POLLING_INTERVAL} seconds...")
            sock.close()
            time.sleep(POLLING_INTERVAL)


# --- Script entry point --- 
# Check if the script is being executed as the main module by using the __name__ variable.
if __name__ == "__main__":
    main()


# | --- Notes regarding possible issues and improvements to implement --- 
# |
# | 1. All config values are hardcoded; could be made configurable via command-line arguments to make it more flexible.
# | 2. TCP connection retries happen only after a full failure; no backoff logic.
# | 3. UDP sends without confirmation - logs may be lost if the server is down.
# | 4. STATE_FILE_PATH is stored on disk without locking - simultaneous runs could overwrite it.
# | 5. If the log file is huge and STATE_FILE_PATH is missing, it will read from start.
# | 6. TCP framing only works if the server expects octet-counted syslog. 
# |    If the server is set to expect newline-terminated messages, this will fail to parse.
# |    Idea: make the framing method configurable (FRAMING="octet" or "newline") to be able to switch without editing code. 
# |    (Using octet framing currently, because testing showed that in my demo environment all log strings were being merged together.)
# | 7. Improvement idea: keep a retry buffer for failed messages so that their sending can be retried on reconnect.
# | 8. If two instances of this script run at the same time (which shouldn't normally happen) on the same log filestate file, 
# |    they can overwrite each other's JSON.
# | 9. If the log file is truncated (not rotated), "seek(last_pos)"" might point beyond EOF, resulting in zero lines read until more are added. 
# |    Idea: implement detection of truncation?
# |  
# |  ...
# |  



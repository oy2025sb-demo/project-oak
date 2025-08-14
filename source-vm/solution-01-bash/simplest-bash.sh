#!/bin/bash

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

# --- Configuration ---
LOG_FILE_PATH="/home/azuregenerator/hw2025.csv"
SYSLOG_SERVER_IP="10.0.0.5"
SYSLOG_SERVER_PORT=55140

# Setting a delay in seconds between sending each log line.
# --- !!! --- NOTE: The sleep utility generally accepts integer arguments representing seconds. 
# However, some implementations allow for floating-point numbers to specify fractions of a second. 
# It is fine now because we use "1", but if we later make it "0.5", it may fail - depending on the environment.
# So, has to be used with some caution.
DELAY_SECONDS="1"

# Setting up batch processing for speedup - helpful if the file is large. 
# Instead of going to sleep after each log line, we can send N lines at once, then sleep. 
# This will send in bursts but still help to avoid flooding the server. 
BATCH_SIZE=4
count=0

# | --- Notes regarding possible issues and improvements to implement --- 
# |  
# | I think this script satisfies the basic requirement of the homework assignment for  
# | "1. Log Reading Tool: Create a tool that reads logs from a file and sends them to a syslog server on a custom port."
# | 
# | It is self-contained, and its execution provides evidence of its function, making it suitable for a small demo.
# | However, it would fall short in the areas of reliability, resilience, performance, and manageability in a production environment, 
# | if compared to dedicated, industry-standard log forwarding agents. 
# | 
# | Among some of the issues, not addressed in this script: 
# | 1. It starts from the beginning of the file every time, not keeping track of which log lines have been successfully sent.
# | 2. If the client restarts while the script is running, log loss would not be prevented.
# | 3. If the syslog server is slow or down, this script would not attempt to slow down sending or retry it.
# | 4. It does not handle log file changes or appends by other processes while it's running.
# | 5. It does not handle possible empty lines in the log file gracefully, if such are present. 
# | 6. All config is hardcoded. Passing the log file path, syslog server, port, etc. as command-line arguments might make the script more flexible.
# |
# | Making this script into a systemd service may help address some of the issues. 
# | Then it would act more like a lightweight log agent that can: 
# |  - be started at boot;
# |  - be restarted on crash;
# |  - run in background;
# |  - survive logout;
# |  - integrate with journalctl system logs, so that the script's output could be checked. 
# |
# | Also, this script should currently be able to handle any plain-text log file where the log entries are separated by newline characters - regardless of file extension.
# |
#  

# Announcing the start of the script and displaying the configuration.
printf ' | Starting Bash log sender script...\n'
printf ' | --------------------------------------------------\n'
printf ' | Source File:      %s\n' "$LOG_FILE_PATH"
printf ' | Destination Host: %s\n' "$SYSLOG_SERVER_IP"
printf ' | Destination Port: %s\n' "$SYSLOG_SERVER_PORT"
printf ' | --------------------------------------------------\n'

printf 'Trying to read the source file...\n'

# Checking if the log file actually exists before trying to read it.
if [[ ! -f "$LOG_FILE_PATH" ]]; then
    # If the file does not exist, print an error message to standard error 'stderr' (>&2) and exit the script with a non-zero status code to indicate failure.
    printf 'Error: Log file not found at %s\n' "$LOG_FILE_PATH" >&2
    exit 1
fi

printf 'Starting log forwarding to %s on port %s.\n' "$SYSLOG_SERVER_IP" "$SYSLOG_SERVER_PORT"


# Reading the log file line by line using a while loop.
# 
# IFS = "Internal Field Separator". By default, read will strip leading/trailing whitespace and split input into multiple variables based on whitespace.
# Setting IFS= before read tells Bash to take the whole line exactly as it is.
# Without IFS=, leading/trailing spaces and tabs will be trimmed in some cases, which can break log parsing.
#
# The -r flag means "don't treat backslashes as escape characters", preventing the interpretation of backslashes.
# Without it, read interprets \n or \\ sequences, which can mangle data. For reading logs, we want -r.
while IFS= read -r line; do
    # For each line read from the file:
    # 1. Print a message to the console to show what is being processed.
    printf '[BASH] Forwarding log: %s\n' "$line"
    
    # Or we could truncate the log line to the first 75 characters for readability instead, if needed:
    #
    # ---
    #
    #printf '[BASH] Forwarding log: %.75s...\n' "$line"
    #
    # ---
    #

    # 2. Use the 'logger' utility to send the line to the remote syslog server and stop if it fails.
    #    -n, --server <name>: Specifies the remote server name or IP.
    #    -P, --port <port>:   Specifies the remote port.
    #    --udp:               Specifies to use the UDP protocol.
    #    --:                  End the argument list. This allows the message line to start with a hyphen (-).
    if ! logger --server "$SYSLOG_SERVER_IP" \
                --port "$SYSLOG_SERVER_PORT" \
                --udp -- "$line"; then
        printf 'Error: Failed to send log line via logger: %s\n' "$line" >&2
        exit 2
    fi

    # We could alternatively use 'nc' (netcat) to send the log line.  
    #    -u:                  Use UDP mode.
    #    -w secs:             Timeout for connects and final net reads. 
    # In this case, -w2 tells netcat to give up/exit after 2 seconds of waiting. 
    #
    # ---
    #
    #if ! printf '%s\n' "$line" | nc -u -w2 "$SYSLOG_SERVER_IP" "$SYSLOG_SERVER_PORT"; then
    #    printf 'Error: Failed to send log line via nc: %s\n' "$line" >&2
    #    exit 2
    #fi
    #
    # ---
    #
    # However, using logger is better than using nc to send the log line over UDP.
    # Using logger ensures that the log message is received and processed correctly by the rsyslog server, which is expecting a message with a specific format. 
    # Using nc would send just the raw text, which may not be parsed correctly.

    # 3. Pause for a short duration after each batch.
    ((count++))
    if (( count % BATCH_SIZE == 0 )); then
        sleep "$DELAY_SECONDS"
    fi

# The 'done < "$LOG_FILE_PATH"' part redirects the file's content into the standard input of the loop.
done < "$LOG_FILE_PATH"

printf '[BASH] Finished sending all logs.\n'

# Exit with a status code of 0 to indicate success.
exit 0

# Log Management System - Homework Assignment Solution (project-oak)

[Homework Assignment](https://github.com/tnurmoja/hw2025)

## Solution Architecture

A high-level overview of the implemented solution.

* **Log Reading Tool:** A simpler Bash script (solution 1) as well as a more complex Python script (solution 2) were developed to read logs from a specified file and forward each log entry to the syslog server on a custom port. 
* **Syslog Server:** rsyslog was configured to listen on the custom port. Logs received are saved to the required directory structure: `/sb/logs/incoming/$year/$month/$day/$fromhost-ip/syslog.log`. The server is also configured to forward the "TRAFFIC" logs to the SIEM.
* **SIEM Tool:** Microsoft Sentinel was used to receive and analyze the forwarded logs from the syslog server with the help of AMA (Azure Monitor Agent). 


## Environment setup

(...)

## Identification of the logs from the provided example

(...)


## Evidence of Completion

This section contains the evidence required to demonstrate the successful implementation of the solution.

### Log Reading Tool Output

(Output from the log reading tool showing the reading and forwarding process)


### Syslog Server Log Files

(Screenshots or listings of saved log files in the correct directory structure on the syslog server)


### SIEM Query Results

(Query results from the SIEM tool confirming that only TRAFFIC logs were received)


### Explanation of the Solution

(...)

## Additional notes

(...)



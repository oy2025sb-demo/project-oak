# Log Management System - Homework Assignment Solution (project-oak)

[Homework Assignment](https://github.com/tnurmoja/hw2025)

## Solution Architecture

A high-level overview of the implemented solution.

* **Log Reading Tool:** A simpler Bash script (solution 1) as well as a more complex Python script (solution 2) were developed to read logs from a specified file and forward each log entry to the syslog server on a custom port. 
* **Syslog Server:** rsyslog was configured to listen on the custom port. Logs received are saved to the required directory structure: `/sb/logs/incoming/$year/$month/$day/$fromhost-ip/syslog.log`. The server is also configured to forward the "TRAFFIC" logs to the SIEM.
* **SIEM Tool:** Microsoft Sentinel was used to receive and analyze the forwarded logs from the syslog server with the help of AMA (Azure Monitor Agent). 


--- 

## Environment setup

(...)

To complete the assignment, a new tenant was set up in Azure.

Log Analytics + Sentinel workspace was created, and 2 Linux virtual machines.

<img width="100%" alt="Sentinel LA workspace" src="https://github.com/user-attachments/assets/251d6dc4-6853-4e2c-bb70-fc633e7a5eaf" />

---

<img width="2283" height="691" alt="VMs" src="https://github.com/user-attachments/assets/74ce8565-6924-4e20-986a-75ffc0d8ea64" />

---
Private IP of the VM from which the logs are sent: 10.0.0.4
<img width="1402" height="175" alt="src private IP" src="https://github.com/user-attachments/assets/efe0860a-3800-492a-9743-64e11fdeb8a8" />


Private IP of the syslog server: 10.0.0.5
<img width="1441" height="172" alt="dst private IP" src="https://github.com/user-attachments/assets/d6d9bc54-7da1-4e1c-b8da-0c5e38ebb3a6" />


(...)

---
## Identification of the logs from the provided example

(...)

---
## Evidence of Completion

This section contains the evidence required to demonstrate the successful implementation of the solution.

### Log Reading Tool Output

(Output from the log reading tool showing the reading and forwarding process)


Bash script run over UDP. Exits upon completion. More details and ideas - in the comments in the script.
Sample logs with headers.

<img width="50%" alt="bash script run - UDP, logs with headers" src="https://github.com/user-attachments/assets/d0e5468e-d119-4065-8cad-cbb7492b9beb" />



And some logs that are just CSV, without headers at the beginning of each line: 
<img width="50%" alt="bash script run - UDP, logs without headers" src="https://github.com/user-attachments/assets/b922f967-bfa5-47f0-9bd2-1702526e7b51" />

-----

Python script run over TCP. Continues to monitor the log file for new lines to be sent + remembers position (see comments in the script for more details). 
Sample logs with headers are used in the example in the screenshot. 

<img width="50%" alt="python script run - TCP, logs with headers" src="https://github.com/user-attachments/assets/6b68d9bb-8a69-4e2a-a766-0ef984f93150" />



And some logs that are just CSV, without headers at the beginning of each line: 

<img width="50%" height="1278" alt="python script run - TCP, logs without headers" src="https://github.com/user-attachments/assets/cc7b0b53-d8a8-4925-bba7-94cdb3ee5458" />


The Python script (solution 2) addresses some of the shortcomings of the Bash script (solution 1).
Look for more details in the comments inside the scripts. :) 

--- 

### Syslog Server Log Files

(Screenshots or listings of saved log files in the correct directory structure on the syslog server)

<img width="50%" alt="server - log directory tree" src="https://github.com/user-attachments/assets/0710cd77-a63c-4da9-bd93-d8a40c1025fe" />




--- 

### SIEM Query Results

(Query results from the SIEM tool confirming that only TRAFFIC logs were received)


--- 

### Explanation of the Solution

(...)

--- 

## Additional notes

(...)


--- 


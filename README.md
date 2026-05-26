# Intelligent-Task-Manager
Developed a Windows-based Intelligent Task Manager and Threat Monitoring System for real-time process tracking, network traffic inspection, malicious IP detection, and hardware privacy monitoring. Implemented Scapy, WMI, multithreading, and Bloom Filter–based threat analysis with forensic logging for cybersecurity auditing.

## Overview

The Intelligent Task Manager & Threat Monitoring System is a Windows-based cybersecurity and system monitoring framework designed for real-time process tracking, network traffic inspection, threat detection, and forensic logging. The project focuses on improving system visibility, detecting suspicious activities, and enhancing privacy and security through continuous monitoring of processes, hardware access, and network behavior.

## Features

* Real-time process and resource monitoring
* Process-chain tracking and hierarchical process visualization
* Live network packet capture and IP threat analysis using Scapy
* Bloom Filter–based malicious IP detection
* Google Safe Browsing API integration for threat intelligence
* Camera and microphone access monitoring with permission control
* Windows Event Log analysis for hardware usage detection
* CSV-based forensic logging and audit trail generation
* Multithreaded architecture for efficient background monitoring
* Security-focused system auditing and anomaly tracking

## Tech Stack

**Language:** Python
**Libraries & Tools:** Scapy, psutil, WMI, ctypes, pybloom-live, pandas, threading, queue, requests, subprocess, Tkinter, CSV, PowerShell

## Key Functionalities

### Process Monitoring

Tracks active system processes, analyzes parent-child process chains, and detects suspicious or unauthorized execution patterns.

### Network Threat Analysis

Captures live packets, extracts IP information, and performs chained threat analysis using:

* Bloom Filter blocklist checks
* Google Safe Browsing API
* Custom reputation-based detection

### Hardware Privacy Monitoring

Monitors camera and microphone usage by detecting active applications, browser sessions, and Windows event logs. Includes system-level permission control and hardware kill-switch functionality.

### Forensic Logging

Maintains structured CSV logs containing timestamps, process activity, IP reputation data, and detected anomalies for audit and investigation purposes.

## Security Benefits

* Enhances visibility into system and network activity
* Detects potentially malicious processes and IPs
* Prevents unauthorized hardware access
* Supports forensic investigations and audit workflows
* Improves privacy and threat awareness

## Future Enhancements

* Machine Learning–based anomaly detection
* Real-time alerting and notification system
* Cross-platform support for Linux and macOS
* Centralized dashboard for visualization and analytics
* Advanced SIEM integration

## Use Cases

* Cybersecurity Monitoring
* Digital Forensics
* Enterprise Security Auditing
* Privacy Protection
* Threat Intelligence Analysis
* System Behavior Analysis

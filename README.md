# Cloud-Based Real-Time Fraud Detection

This project demonstrates a **cloud-inspired real-time data processing pipeline** for fraud detection, implemented locally using **Docker-based microservices**. The system follows data engineering principles such as scalability, reliability, and reproducibility.

## System Overview
The architecture consists of three main components:
- **Kafka** as a distributed message broker for real-time event ingestion
- **Apache Spark Structured Streaming** for stream processing and aggregation
- **Python-based Producer** to simulate transactional data streams

All components are deployed as isolated Docker containers and orchestrated using Docker Compose.

## How It Works
1. A Python producer generates simulated transaction events and publishes them to a Kafka topic.
2. Kafka acts as a buffer and ingestion layer for streaming data.
3. Spark consumes the stream from Kafka, performs real-time processing, and computes simple aggregations that could be used for fraud detection.

## Reproducibility & Maintainability
- The entire infrastructure is defined as **Infrastructure as Code (IaC)** using Docker Compose.
- The system can be reproduced on any machine with Docker installed.
- The microservice-based architecture supports scalability and maintainability.

## Notes
- This project is developed for **educational purposes**.
- The implementation focuses on demonstrating core real-time data engineering concepts rather than production readiness.
- The system can be extended with monitoring, security, and fault-tolerance mechanisms.

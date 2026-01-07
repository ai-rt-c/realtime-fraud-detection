\# System Architecture



The system follows a microservice-based data processing architecture designed for real-time data ingestion and analysis.



\## Components



\- \*\*Kafka \& Zookeeper\*\*  

&nbsp; Responsible for reliable message streaming and coordination.



\- \*\*Producer Service (Python)\*\*  

&nbsp; Simulates real-time data and publishes messages to Kafka topics.



\- \*\*Apache Spark Structured Streaming\*\*  

&nbsp; Consumes streaming data from Kafka, performs preprocessing and aggregation.



\## Architecture Design



The architecture was designed during the conception phase and implemented during the development phase using Docker containers.

All services are deployed locally using Docker Compose.




Course contents  
**Data Engineering Bootcamp**

**Table of contents**

 - [Course Duration](#course-duration)
 - [Course Overview](#course-overview)
 - [Learning Outcomes](#learning-outcomes)
 - [Course Details](#course-details)
   - [Unit 0: Prework](#unit-0-prework)
   - [Unit 1: Programming & Data Foundations](#unit-1-programming-data-foundations)
   - [Unit 2: Designing Data Pipelines & Big Data Systems](#unit-2-designing-data-pipelines-big-data-systems)
   - [Unit 3: Cloud & Real-Time Data Engineering](#unit-3-cloud-real-time-data-engineering)
   - [Unit 4: Ensuring Data Reliability and Governance](#unit-4-ensuring-data-reliability-and-governance)
   - [Unit 5: Capstone Project](#unit-5-capstone-project)
 - [Assessment](#assessment)
 - [Materials Provided](#materials-provided)
 - [Tools Needed](#tools-needed)

## **Course Duration** {#course-duration}

* **Total:** 360 hours + 40 hours prework  
* **Format:** 9 weeks × 40 hours/week (e.g., 8h/day)  
* **Delivery:** Instructor-led, remote, highly practical and project-based

## **Course Overview** {#course-overview}

This bootcamp equips learners to become job-ready data engineers who design, build, and maintain the pipelines that power analytics and AI. 

Through a hands-on, project-based curriculum, students gain proficiency in Python, SQL, and modern data frameworks like Airflow, dbt, Spark, and Kafka, while learning to manage cloud data warehouses such as Snowflake, BigQuery, and Redshift. 

The course emphasizes real-world data workflows, including pipeline orchestration, real-time streaming, data governance, and CI/CD for deployment. 

By graduation, students can confidently build and deploy production-grade, cloud-native data systems, ready to take on roles as Junior Data Engineers, ETL Developers, or Pipeline Engineers in modern data teams.

## **Learning Outcomes** {#learning-outcomes}

* Design and implement complete ETL and ELT pipelines using Python, SQL, Apache Airflow, and dbt.

* Develop scalable data processing workflows with Apache Spark for both batch and streaming datasets.

* Deploy and operate cloud data warehouses such as Snowflake, BigQuery, or Redshift (or similar of the same kind) for analytical and reporting use cases.

* Build and manage real-time data pipelines using Apache Kafka and NiFi (or similar of the same kind) for live data ingestion and transformation.

* Design and maintain data models, validation checks, and governance frameworks to ensure data accuracy, lineage, and regulatory compliance.

* Automate infrastructure and pipeline deployments using CI/CD practices with Docker and Terraform.

* Implement monitoring, logging, and optimization strategies to maintain reliable, high-performance data systems.

* Deliver and present deployable capstone projects that demonstrate end-to-end proficiency in data engineering tools, workflows, and problem-solving.


## **Course Details** {#course-details}

### **Unit 0: Prework** {#unit-0-prework}

**Duration:** Self-paced (40 hours completed before bootcamp start)  
**Topics:**

* Introduction to Python: understanding syntax, variables, and simple functions  
* Basics of SQL: retrieving and filtering data from a database  
* Working with data in Pandas: reading, cleaning, and organizing CSV files  
* Introduction to Git: saving and sharing your work using version control  
* Overview of how data flows in organizations (from raw data to reports)  
* Setting up your tools: installing Python, Jupyter Notebook, and VS Code

**Example Activities:**

* Write a short Python script that reads a CSV file and counts total rows  
* Use basic SQL commands to find the top 5 customers from a sample sales table  
* Open a dataset in Pandas and remove missing or duplicate values  
* Create your first GitHub repository and upload a simple Python file  
* Draw a simple diagram showing how raw data turns into a business dashboard

**Outcome:**  
After completing the pre-work, students will:

* Understand basic coding concepts  
* be comfortable using data tools like Python and SQL  
* know how data is stored and organized  
* Create a solid foundation for the bootcamp

### **Unit 1: Programming & Data Foundations** {#unit-1-programming-data-foundations}

Week 1: Programming Foundations

**Duration:** Week 1 (40 hours)  
**Topics:**

* Core Python programming: syntax, control flow, functions, and Jupyter Notebooks  
* Data analysis with Pandas: creating and manipulating DataFrames, filtering, aggregations, and joins  
* Introduction to NumPy: arrays, slicing, and vectorized operations for performance  
* Data transformation and ETL basics using Python and Pandas  
* Advanced SQL: joins, subqueries, CTEs, and window functions for analytics

**Example Activities:**

* Write a Python script to read and summarize CSV data  
* Clean and analyze a public dataset using Pandas  
* Compare vectorized NumPy operations to standard Python loops  
* Build a small ETL workflow combining multiple CSV files  
* Run advanced SQL queries on telecom or banking datasets to extract insights

**Outcomes:**

* Understand Python syntax, control flow, and functions for data manipulation tasks  
* Develop the ability to clean, filter, and analyze datasets using Pandas  
* Gain proficiency in using NumPy for high-performance numerical processing  
* Build and automate small-scale ETL processes with multiple data sources  
* Write optimized SQL queries for data extraction, analysis, and business insights

Week 2: Data Modeling and Storage Systems

**Duration:** Week 2 (40 hours)

**Topics:**

* Fundamentals of relational and NoSQL databases (ACID vs. BASE, schema flexibility)  
* Schema design, normalization, and denormalization for scalable data models  
* Data lake and data warehouse architectures: schema-on-read vs. schema-on-write  
* Query optimization, indexing, and storage performance techniques  
* Common data formats: CSV, Parquet, Avro, ORC, and their trade-offs

**Example Activities:**

* Design an ER diagram for a banking system and simulate it in MongoDB  
* Create normalized and denormalized schemas using PostgreSQL  
* Load JSON data into a data lake and query it with Athena or Spark  
* Perform CRUD and aggregation operations in SQL and NoSQL databases  
* Benchmark query performance for CSV vs. Parquet files

**Outcomes:**

* Differentiate between relational and NoSQL data models and their ideal use cases  
* Design and implement normalized, scalable, and efficient database schemas  
* Understand the structure and operation of data lakes and warehouses  
* Execute and optimize queries across SQL and NoSQL environments  
* Choose appropriate file formats and indexing methods for analytical workloads

### **Unit 2: Designing Data Pipelines & Big Data Systems** {#unit-2-designing-data-pipelines-big-data-systems}

Week 3: ETL and ELT Pipelines

**Duration:** Week 3 (40 hours)

**Topics:**

* ETL and ELT fundamentals: batch vs. streaming, pipeline layering, and orchestration  
* Designing and automating data workflows for ingestion and transformation  
* Apache Airflow concepts: DAGs, operators, scheduling, dependencies, and failure recovery  
* dbt for in-warehouse transformations: modular models, testing, and lineage tracking  
* Integrating Airflow and dbt for end-to-end data workflow management

**Example Activities:**

* Diagram and explain an ETL pipeline from raw data to warehouse  
* Write a Python ETL script and schedule it using cron  
* Build and execute DAGs in Apache Airflow for workflow automation  
* Create dbt models and visualize their dependencies and lineage  
* Add retries, branching, and alerts to Airflow DAGs for fault tolerance

Project 1: Build an automated data pipeline using Airflow and dbt to extract, transform, and load data into a warehouse.

Design and implement an automated ETL/ELT pipeline using **Apache Airflow** and **dbt** to extract, transform, and load data into a cloud data warehouse. The project will include scheduling, dependency management, transformation testing, and lineage documentation.

**Outcomes:**

* Understand the architecture and components of modern ETL and ELT pipelines  
* Build and automate batch data workflows using Python and scheduling tools  
* Use Apache Airflow to orchestrate multi-step data pipelines  
* Design modular and testable transformations using dbt  
* Deploy a complete automated data pipeline integrating Airflow and dbt

### 

Week 4: Big Data Frameworks with Apache Spark

**Duration:** Week 4 (40 hours)

**Topics:**

* Introduction to Apache Spark: RDDs, DataFrames, and distributed transformations  
* PySpark fundamentals: SparkSession, lazy evaluation, and data pipelines  
* Spark performance optimization: Catalyst optimizer, caching, and query planning  
* Partitioning, shuffling, and tuning for parallelism and scalability  
* Understanding distributed system architecture: drivers, executors, and cluster management

**Example Activities:**

* Use `sc.parallelize()` to perform distributed data transformations  
* Load and transform large CSV datasets with PySpark and save the output  
* Analyze and optimize Spark queries using `.explain()` and the Spark UI  
* Tune partitioning strategies to improve throughput and reduce shuffle costs  
* Explore fault tolerance and execution flow in Spark through the Spark Web UI

**Outcomes:**

* Understand Spark’s distributed computing model and its core components  
* Build scalable data processing pipelines using PySpark  
* Optimize Spark transformations for performance and efficiency  
* Apply partitioning and parallelism strategies to large data workloads  
* Interpret Spark execution plans and logs to troubleshoot and monitor jobs

### **Unit 3: Cloud & Real-Time Data Engineering** {#unit-3-cloud-real-time-data-engineering}

Week 5: Cloud Data Warehousing

**Duration:** Week 5 (40 hours)

**Topics:**

* Overview of major cloud data warehouses: Snowflake, BigQuery, and Redshift  
* Setting up, provisioning, and managing warehouse environments  
* Multi-cloud strategies: interoperability, replication, and cost optimization  
* Infrastructure as Code (IaC) using Terraform and Docker for automation  
* Designing end-to-end analytical data pipelines: ETL, transformation, and reporting

**Example Activities:** 

* Compare query performance and cost across Snowflake, BigQuery, and Redshift  
* Load and query datasets in a cloud warehouse using SQL  
* Integrate pipelines that connect multiple cloud providers  
* Use Terraform to deploy cloud data infrastructure reproducibly  
* Build an end-to-end pipeline that ingests, transforms, and stores data for analytics

**Outcome:**

* Understand and evaluate key cloud data warehousing platforms and architectures  
* Confidently manage, configure, and query cloud warehouse environments  
* Design vendor-neutral, cost-efficient, and scalable cloud data solutions  
* Automate infrastructure deployment using Terraform and Docker  
* Deliver a complete, cloud-based analytical pipeline ready for reporting

Week 6: Streaming and Real-Time Data Processing

**Duration:** Week 6 (40 hours)

**Topics:**

* Fundamentals of real-time data pipelines using Apache Kafka  
* Event-driven architecture: producers, brokers, topics, consumers, and offset management  
* Stream transformations and micro-batching using Spark Structured Streaming  
* Visual flow orchestration and routing with Apache NiFi  
* Cloud streaming services: AWS Kinesis, Google Pub/Sub, and Azure Event Hubs (or similar of the same kind)  
* Real-time monitoring and analytics dashboards

**Example Activities:** 

* Create a Kafka producer-consumer demo to simulate live event streams  
* Manage consumer groups and offsets for parallel data consumption  
* Build a Spark Streaming ETL job connected to Kafka topics  
* Design and deploy a NiFi flow for ingesting and routing real-time data  
* Compare performance and latency across cloud streaming services

**Project 2: Real-Time Data Ingestion and Analytics Pipeline**

Build a real-time data pipeline using Kafka and Spark Streaming that ingests and processes live event data, then visualizes insights on a dashboard. The project will demonstrate end-to-end real-time processing, including ingestion, transformation, storage, and visualization.

**Outcome:**

* Understand the principles and components of real-time data streaming systems  
* Build and scale event-driven pipelines using Kafka and Spark Streaming (or similar of the same kind)  
* Integrate NiFi for visual data routing and orchestration  
* Evaluate and compare cloud streaming frameworks for scalability and performance  
* Deliver a live dashboard showcasing streaming data insights in real time

### **Unit 4: Ensuring Data Reliability and Governance** {#unit-4-ensuring-data-reliability-and-governance}

**Duration:** Week 7 (40 hours)

**Topics:**

* Fundamentals of data validation and testing frameworks for reliable pipelines  
* Data profiling and anomaly detection using statistical and rule-based approaches  
* Metadata management and documentation for transparency and discoverability  
* Data privacy, masking, and compliance with regulations like GDPR  
* Lineage tracking and auditing for source-to-target data traceability

**Example Activities:** 

* Create validation rules and automated checks using Great Expectations  
* Generate and analyze data quality reports for completeness and accuracy  
* Use dbt documentation to visualize model lineage and schema metadata  
* Mask sensitive data fields and implement privacy controls on real-world datasets  
* Build a data lineage graph combining Airflow metadata and dbt documentation

**Outcome:**

* Implement validation frameworks to ensure pipeline accuracy and reliability  
* Measure and monitor data quality through profiling and reporting  
* Document and visualize metadata for transparency and collaboration  
* Apply governance practices for privacy, compliance, and auditability  
* Build traceable data pipelines with complete lineage and quality assurance

### **Unit 5: Capstone Project** {#unit-5-capstone-project}

**Duration:** Week 8-9 (80 hours)

**Project Part I: Banking Real-Time Transaction Pipeline**

Design and implement a real-time financial transaction processing pipeline that integrates ingestion, transformation, storage, orchestration, and reporting layers using modern data engineering tools. The project simulates a Central Bank scenario that processes continuous transaction feeds from multiple banks, ensuring data reliability, fault tolerance, and compliance.

**Example Activities:** 

* Design the pipeline architecture and data flow from ingestion to reporting.  
* Build multi-source ingestion flows using NiFi and Kafka topics.  
* Implement real-time validation and enrichment using Spark Streaming and dbt.  
* Orchestrate workflows with Airflow and deploy on a cloud environment (AWS/GCP).  
* Validate data quality, implement lineage tracking, and visualize insights on Superset or Power BI.

**Outcome:**

* Build a real-time data ingestion and transformation pipeline for financial transactions.  
* Apply data validation, enrichment, and lineage tracking for audit-ready systems.  
* Automate workflow orchestration and monitoring using Airflow and Great Expectations.  
* Deploy a cloud-based, production-style pipeline integrating both batch and streaming data.  
* Deliver a working regulatory analytics dashboard demonstrating data integrity and reliability.

**Project Part II: Telecom CDR Streaming and Governance System**

Implement an enterprise-scale telecom data engineering pipeline that can ingest, process, and govern high-volume Call Detail Records (CDRs) in real time. This project emphasizes data privacy, governance, and compliance, focusing on anonymization, lineage tracking, and low-latency analytics for operational insights.

**Example Activities:** 

* Define the system architecture and design a governance-enabled streaming pipeline.  
* Ingest CDR data using NiFi and stream it through Kafka topics segmented by region and call type.  
* Process and anonymize CDRs using Spark Streaming; model final datasets using dbt.  
* Implement workflow orchestration, data validation, and lineage tracking using Airflow and Great Expectations.  
* Visualize network metrics and call quality data in Superset; present technical documentation and results.

**Outcome:**

* Build a real-time telecom CDR streaming pipeline capable of handling millions of records.  
* Apply data masking and anonymization techniques for compliance and privacy.  
* Implement automated governance and lineage tracking to ensure data transparency.  
* Orchestrate and monitor pipelines using Airflow with quality checks via Great Expectations.  
* Deliver a fully documented, production-grade telecom data system with real-time dashboards and compliance reporting.

## **Assessment** {#assessment}

* **Formative:** Daily labs, peer reviews, instructor feedback

* **Mid-Term Project 1 Week 3 – Automated Data Pipeline with Airflow and dbt:**  
  * **Duration:** Week 3 \[16 hours\]  
  * **Project:**   
  * Design and implement a mini end-to-end batch pipeline that extracts raw data, transforms it using dbt, and orchestrates the workflow using Apache Airflow. The project simulates a real-world ETL process for a small analytics team.  
  * **Outcome:**   
  * Students will demonstrate the ability to build a production-style automated data pipeline, integrating Airflow and dbt for workflow orchestration, transformation testing, and reporting.

* **Mid-Term Project 2 Week 6- Real-Time Data Ingestion and Analytics Pipeline:**  
  * **Duration:** Week 6 (16 hours)  
  * **Project:**   
  * Build a **real-time data pipeline** that streams, processes, and visualizes live data using **Kafka** and **Spark Streaming**, ending with a live dashboard for analytics.  
  * **Outcome:**  
  * Students will gain practical experience in **real-time data engineering**, showcasing their ability to design streaming workflows and deliver operational dashboards for business insights

* **Capstone Sprint Project Week 8-9 (Major Deliverable):**  
  * **Duration:** Weeks 8-9 \[80 hours\]  
  * **Project:**   
  * **Banking Transaction Pipeline** – A real-time financial system that processes, validates, and enriches live transactions from multiple banks.  
  * **Telecom CDR Streaming & Governance System** – A telecom-scale platform for ingesting, anonymizing, and monitoring millions of daily call records while ensuring compliance and traceability.  
* **Topics:**   
  * Streaming architecture (Kafka, Spark Streaming)  
  * Data governance and lineage (dbt docs, Great Expectations)  
  * Cloud deployment and orchestration (Airflow, Terraform)  
  * Real-time visualization (Superset, Power BI)  
  * Privacy and compliance (GDPR, PII masking)  
* **Outcome:**  
  * Students will demonstrate full-stack **data engineering competence**, from ingestion and transformation to governance and cloud deployment. They’ll graduate with **portfolio-ready projects** that validate readiness for roles such as **Junior Data Engineer, ETL Developer, or Data Pipeline Engineer**.

## **Materials Provided** {#materials-provided}

**For students:**

* Comprehensive lesson slides and topic notes for all units   
* Hands-on lab exercises and guided coding notebooks for daily practice  
* Project templates for capstone builds

**For instructors:**

* Instructor guide with detailed unit outcomes and teaching notes  
* Course roadmap with weekly pacing, milestones, and timing estimates  
* Lesson plans outlining objectives, key discussion points, and example walkthroughs  
* Lab solution sets with explained code samples and troubleshooting tips  
* Evaluation rubrics for project grading, peer reviews, and capstone presentations

## **Tools Needed** {#tools-needed}

* Python (v3.10 or higher) – for scripting and data transformation  
* SQL – for querying and data modeling across relational systems  
* Apache Airflow – workflow orchestration and scheduling  
* dbt (Data Build Tool) – modular in-warehouse transformations and testing  
* Apache Spark (PySpark) – distributed data processing for batch and streaming jobs  
* Apache Kafka – real-time data streaming and messaging  
* Apache NiFi – visual data ingestion and flow automation  
* Great Expectations – for data validation and quality testing  
* Google Cloud Platform (BigQuery, Pub/Sub, Storage) or AWS (Redshift, S3, Kinesis)  
* Snowflake – for cloud data warehousing and analytics  
* Terraform & Docker – for infrastructure automation and environment reproducibility  
* GitHub/GitLab – version control and project collaboration  
* VS Code / Jupyter Notebook – for coding, notebooks, and lab submissions  
* Apache Superset / Power BI – for dashboarding and visualization  
* Or similar tools of the same kind
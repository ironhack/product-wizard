Course contents  
**DevOps and Cloud Computing**

**Table of contents**

 - [Unit 0: Prework](#unit-0-prework)
 - [Unit 1: Fundamentals of DevOps and Scrum Framework](#unit-1-fundamentals-of-devops-and-scrum-framework)
 - [Unit 2: AWS Cloud Computing](#unit-2-aws-cloud-computing)
 - [Unit 3: Infrastructure as Code (IaC) with Terraform and Ansible](#unit-3-infrastructure-as-code-iac-with-terraform-and-ansible)
 - [Unit 4: Containerization with Docker](#unit-4-containerization-with-docker)
 - [Project 1: Multi-Stack DevOps Infrastructure Automation](#project-1-multi-stack-devops-infrastructure-automation)
 - [Unit 5: Kubernetes Orchestration](#unit-5-kubernetes-orchestration)
 - [Unit 6: CI/CD and Managed Kubernetes with Amazon EKS](#unit-6-cicd-and-managed-kubernetes-with-amazon-eks)
 - [Project 2: End-to-End Deployment with Amazon EKS and CI/CD](#project-2-end-to-end-deployment-with-amazon-eks-and-cicd)
 - [Unit 7: Advanced Azure Cloud Operations and Infrastructure Automation](#unit-7-advanced-azure-cloud-operations-and-infrastructure-automation)
 - [Unit 8: Azure Governance, Kubernetes on Azure (AKS), and Monitoring with Prometheus & Grafana](#unit-8-azure-governance-kubernetes-on-azure-aks-and-monitoring-with-prometheus-grafana)
 - [Project 3 (Final Capstone): End-to-End DevOps Deployment](#project-3-final-capstone-end-to-end-devops-deployment)

This 400-hour course (comprising 40 hours of prework and 360 hours of instruction) provides a comprehensive introduction to DevOps, enabling students to master the skills necessary for modern software development and operations. Covering topics from Linux fundamentals to monitoring and observability, students will work with industry-standard tools across infrastructure provisioning, containerization, orchestration, and continuous integration and deployment. The program concludes with a capstone project where students apply what they’ve learned in a realistic DevOps scenario.

**Learning Objectives**

1. Understand and implement fundamental DevOps practices, including version control with Git and agile methodologies such as Scrum.  
2. Build and deploy scalable applications using Linux, Apache, and Nginx on cloud platforms.  
3. Utilize AWS for infrastructure setup and management, including IAM, VPC, and EC2 services.  
4. Apply Infrastructure as Code principles using Terraform to automate the provisioning of cloud resources.  
5. Manage configuration and deployment processes using Ansible.  
6. Containerize applications and manage container orchestration using Docker and Kubernetes.  
7. Implement continuous integration and continuous deployment (CI/CD) pipelines using GitHub Actions and SonarQube.  
8. Monitor and maintain application performance using Prometheus and Grafana.  
9. Apply security best practices in cloud and DevOps environments, including IAM, encryption, and compliance.  
10. Work effectively in teams, manage projects using agile methodologies, and present technical solutions in sprint reviews.  
11. Receive and integrate feedback to improve DevOps solutions.  
12. Demonstrate proficiency in a final capstone project, showcasing the ability to apply DevOps principles to real-world problems.

## **Unit 0: Prework**

**Objective:**

By the end of the prework phase, students should be able to understand and apply fundamental DevOps concepts, including Linux basics, scripting for automation, network fundamentals and Git for version control. Additionally, students will gain an introductory understanding of cloud systems and DevOps principles, fostering collaboration, efficiency, and high-quality software delivery.

**Description:**

The prework phase is designed to introduce students to the foundational elements of DevOps. It covers essential topics such as Linux basics, scripting for task automation, network fundamentals, Git for version control, and an overview of cloud systems. Through this unit, students will develop the necessary skills to manage systems, automate tasks, and begin developing applications, setting the stage for success in the dynamic DevOps field.

**Topics:**

* Linux & Scripting  
* Network Fundamentals  
* Git and Version Control  
* Culture of DevOps and DevOps Introduction  
* Overview of Cloud Systems (AWS, Azure)

**Tools:**

* Linux  
* Git  
* AWS  
* Azure

## **Unit 1: Fundamentals of DevOps and Scrum Framework**

**Objective:** By the end of this unit, students should be able to explain core DevOps principles, use Git for version control, navigate Linux environments, and collaborate using agile practices such as Scrum.

**Description:** This unit introduces the foundational tools and practices of DevOps. Students will explore the DevOps lifecycle and team culture, dive into version control with Git and GitHub, and begin working in Linux command-line environments. The unit also introduces agile frameworks, particularly Scrum, and highlights how modern development teams plan, prioritize, and deliver work collaboratively. A formative assessment on Linux is included to ensure foundational system skills.

**Topics:**

* DevOps fundamentals: culture, lifecycle, team collaboration  
* Linux terminal navigation and basic shell commands  
* Git basics: repositories, commits, branches, and merges  
* GitHub collaboration: pull requests, forks, issues  
* GitFlow workflow  
* Introduction to Scrum and agile ceremonies  
* Introduction to continuous feedback and delivery pipelines

**Tools:**

* Git, GitHub  
* Linux/Ubuntu CLI  
* Trello or Jira for agile task management

##  **Unit 2: AWS Cloud Computing**

**Objective:** Use core AWS services to architect, provision, and manage secure and scalable infrastructure environments essential for DevOps operations.

**Description:** This unit introduces students to the foundational services and architecture of Amazon Web Services (AWS). Students will work hands-on with identity and access management (IAM), virtual private cloud (VPC) networking, EC2 instances, and the AWS CLI. Through guided and challenge labs, they will build and secure infrastructure, automate service configuration, and deploy scalable compute resources. The unit culminates with monitoring strategies using CloudWatch and an introduction to infrastructure automation with CloudFormation.

**Topics:**

* Introduction to Cloud Computing and AWS  
* IAM: Users, Groups, Policies, Access Keys  
* AWS CLI installation and configuration  
* VPCs, subnets, peering, route tables, and security groups  
* EC2 deployment and custom AMIs  
* Load Balancing with ELB and Auto Scaling  
* AWS Lambda and serverless compute  
* S3, EBS storage, and static site hosting  
* RDS and DynamoDB databases  
* AWS CloudWatch for monitoring  
* Introduction to AWS CloudFormation  
* Security best practices and automation with Python and boto3

**Tools:**

* AWS Console  
* AWS CLI  
* EC2, S3, VPC, IAM  
* CloudWatch, ELB, RDS  
* Lambda, CloudFormation  
* Python & boto3 (for automation)

## **Unit 3: Infrastructure as Code (IaC) with Terraform and Ansible**

**Objective:** Automate infrastructure provisioning and configuration management using Terraform for cloud environments and Ansible for system automation.

**Description:** This unit focuses on declarative infrastructure and provisioning workflows using modern Infrastructure as Code (IaC) tools. Students begin by mastering Terraform’s configuration language (HCL), variables, and state management. They will create reusable infrastructure modules, integrate with AWS, and manage remote state. The second part of the unit introduces Ansible: writing inventory files, playbooks, using roles, vaults, and Jinja2 templates for provisioning configuration. Through practical labs and assessments, students build real-world environments using both tools, combining automation with reliability and scalability.

**Topics:**

* Infrastructure as Code concepts and workflow  
* Terraform setup, HCL syntax, and CLI usage  
* Variables, modules, state files (local and remote)  
* Meta-arguments (count, for\_each) and functions  
* Building custom reusable modules  
* Ansible basics and architecture  
* YAML syntax and inventory files  
* Ad-hoc commands and playbooks  
* Ansible variables, templates (Jinja2), and roles  
* Server automation using playbooks and roles  
* Secure secrets with Ansible Vault

**Tools:**

* Terraform (HCL)  
* AWS CLI (for integration)  
* Ansible  
* YAML  
* Jinja2 templates

## **Unit 4: Containerization with Docker**

**Objective:** Containerize and manage applications using Docker to build scalable, portable, and isolated environments suitable for modern deployment workflows.

**Description:** In this unit, students will gain a solid foundation in containerization by working with Docker. They will explore the benefits of containerized applications versus traditional deployment models and practice building and deploying web apps using Docker. Key concepts include monolithic vs. microservices architecture, Docker networking and storage, image creation, and multi-container setups using Docker Compose. Labs include real-world scenarios such as deploying Node.js and Java applications, building microservices, and integrating storage and networking strategies.

**Topics:**

* Introduction to containers and Docker  
* Installing and configuring Docker Engine  
* Monolithic vs. microservices architecture  
* Docker CLI and core commands  
* Dockerfiles, images, and multi-stage builds  
* Deploying Node.js and Java apps with Docker  
* Docker networking and storage concepts  
* Docker Compose for multi-container applications  
* Troubleshooting Docker environments  
* Introduction to container security practices

**Tools:**

* Docker  
* Docker Compose  
* Node.js, Java (for containerized app examples)  
* Tshark (for network sniffing labs)  
* MySQL (in containerization labs)

## 

## **Project 1: Multi-Stack DevOps Infrastructure Automation**

**Objective:** Apply the skills acquired in the previous units covering DevOps principles, version control, cloud provisioning with AWS, infrastructure automation, and containerization to deploy a full-stack microservices application using real-world tools and workflows.

**Description:** This project challenges students to collaboratively deploy a polyglot microservices-based voting application, integrating multiple languages (Python, Node.js, C\#), databases (Redis and PostgreSQL), and containerization strategies. Working as an agile team, students will provision cloud infrastructure on AWS using Terraform, configure environments using Ansible, containerize services with Docker, and manage multi-service deployment using Docker Compose. The project simulates a production-like scenario, reinforcing all topics from previous units and providing hands-on experience with cross-service networking, environment management, and secure infrastructure design.

**Deliverables:**

* A GitHub repository with Terraform and Ansible configuration, Dockerfiles, and final project code.  
* A deployed system demonstrating container orchestration and communication across services in AWS.  
* A 15-minute live demo and presentation simulating a final sprint review, showcasing team workflow and technical implementation.

## **Unit 5: Kubernetes Orchestration**

**Objective:** Deploy and manage containerized applications using Kubernetes, understanding its architecture and core components for scalable orchestration.

**Description:**

This unit introduces students to Kubernetes, the industry-standard system for automating the the deployment, scaling, and management of containerized applications. After completing their first project, students dive into Kubernetes fundamentals, learning to work with clusters, pods, services, namespaces, deployments, and updates. Through practical labs, students deploy single and multi-tier applications using kubectl and explore features like ConfigMaps, Secrets, and rolling updates. Additional tools like Minikube and k9s support local experimentation and visualization.

**Topics:**

* Introduction to Kubernetes  
* Kubernetes architecture and cluster concepts  
* kubectl CLI for resource management  
* Pods, ReplicaSets, Deployments  
* Namespaces and service discovery  
* ConfigMaps and Secrets  
* Rolling updates and deployment strategies  
* Multi-tier app deployment (Guestbook, Redis)  
* Persistent storage and troubleshooting practices  
* Local deployment with Minikube

**Tools:**

* Kubernetes  
* kubectl  
* Minikube  
* k9s

##  **Unit 6: CI/CD and Managed Kubernetes with Amazon EKS**

**Objective:** By the end of this unit, students will be able to manage Kubernetes clusters on Amazon Web Services using EKS, apply advanced deployment strategies (e.g., Ingress, PVCs, LoadBalancers), and implement CI/CD pipelines using GitHub Actions and SonarQube for quality control.

**Description:** This unit extends students’ container orchestration knowledge by introducing Amazon Elastic Kubernetes Service (EKS) and the use of managed Kubernetes clusters in the cloud. Through a mix of guided labs and configuration tasks, learners create and manage EKS clusters using eksctl, deploy real-world applications, and explore best practices around volumes, ingress, and services. The second half of the unit introduces DevOps automation with CI/CD pipelines using GitHub Actions and code quality assurance with SonarQube. The unit culminates in deploying a 3-tier Java application on both EC2 and EKS, preparing learners for complex cloud-native deployments.

**Topics:**

* Amazon EKS: Setup and architecture  
* Creating clusters with eksctl  
* Kubernetes LoadBalancers, PVCs, and Volumes  
* NGINX deployment and Ingress controllers on EKS  
* GitHub Actions for CI/CD pipelines  
* Continuous Integration concepts  
* Code quality and security analysis with SonarQube  
* StatefulSets in Kubernetes *(optional)*  
* Multi-tier app deployment on AWS using EKS and EC2

**Tools:**

* Amazon EKS  
* eksctl  
* GitHub Actions  
* SonarQube  
* Kubernetes  
* Docker

## **Project 2: End-to-End Deployment with Amazon EKS and CI/CD**

**Objective:** Apply cloud-native DevOps principles to deploy a full-stack microservices application on Amazon EKS using Kubernetes, Ingress, and GitHub Actions CI/CD.

**Description:** In this milestone project, students consolidate their knowledge from Units 1–6 by deploying a multi-service Voting App to a production-grade environment on Amazon EKS. They will provision infrastructure with eksctl, deploy services like Redis and Postgres, and orchestrate microservices (vote, result, worker) using Kubernetes manifests. To route traffic, they will configure an NGINX Ingress Controller via Helm. For automation, students will implement a full CI/CD pipeline with GitHub Actions that builds Docker images, pushes them to a registry, and deploys updates directly to EKS. This project simulates real-world cloud deployment workflows and emphasizes automation, scalability, and security.

**Deliverables:**

* Fully functional Voting App deployed on Amazon EKS  
* Kubernetes manifests for each microservice and supporting services  
* Helm-configured NGINX Ingress for traffic routing  
* GitHub repository with:  
  * Source code and Dockerfiles  
  * GitHub Actions workflow for CI/CD  
  * Access to deployed endpoints (/vote, /result)  
* Documentation and demo walkthrough (optional)

##  **Unit 7: Advanced Azure Cloud Operations and Infrastructure Automation**

**Objective:** By the end of this unit, students will be able to architect, deploy, monitor, and secure infrastructure and applications using Microsoft Azure services and Infrastructure as Code (IaC) with Terraform.

**Description:** This unit expands students’ understanding of cloud infrastructure management with a deep dive into Microsoft Azure. The focus is on provisioning and managing compute, networking, and storage resources within Azure, while applying best practices in security, cost control, and DevOps automation. Students will gain hands-on experience deploying both Linux and Windows VMs, creating web apps, configuring identity and access management (IAM) with Microsoft Entra, and implementing monitoring and alerting tools. The unit concludes with Terraform-based infrastructure provisioning and modularization, allowing students to automate the deployment of scalable, reusable cloud infrastructure.

**Topics:**

* Core architectural components of Azure  
* Azure compute services: Linux & Windows virtual machines, web apps  
* Azure networking and storage fundamentals  
* Azure Identity & Access: IAM, RBAC, Microsoft Entra  
* Zero Trust and defense-in-depth security models  
* Azure cost management and monitoring  
* Infrastructure as Code (IaC) with Terraform  
* Automating VM and network provisioning  
* Azure CLI and automation tools

**Tools:**

* Microsoft Azure  
* Azure CLI  
* Azure Portal  
* Microsoft Entra (formerly Azure Active Directory)  
* Terraform  
* Storage Explorer & AzCopy

##  **Unit 8: Azure Governance, Kubernetes on Azure (AKS), and Monitoring with Prometheus & Grafana**

**Objective:** By the end of this unit, students will be able to manage Kubernetes clusters in Microsoft Azure using AKS, apply governance and compliance strategies, and implement comprehensive observability using Prometheus, Grafana, and Loki.

**Description:** This unit introduces students to Azure governance and security features, including resource locks, policy, and cost control. It then dives into managing Azure Kubernetes Service (AKS) for orchestrating containerized applications, culminating in deploying a 3-tier application. The second part of the unit transitions into monitoring and observability, where students will learn the fundamentals of metrics, monitoring, and alerting using Prometheus, Grafana, and Loki across cloud-native and containerized environments. The hands-on labs progressively move from monitoring VMs and Docker containers to advanced Kubernetes monitoring and logging.

**Topics:**

* **Azure Governance and AKS**  
  * Azure governance, compliance, and resource locks  
  * Managing and deploying Azure resources  
  * Deploying apps to Azure Kubernetes Service (AKS)  
  * Ingress and exposure for AKS workloads  
* **Monitoring & Observability**  
  * Concepts: Monitoring vs Observability  
  * Metrics and logs in distributed systems  
  * Prometheus fundamentals and PromQL  
  * Grafana dashboards and alerts  
  * Monitoring VMs, Docker containers, and Kubernetes clusters  
  * Logging with Grafana Loki  
  * Using Azure Managed Grafana and Terraform integration

**Tools:**

* Microsoft Azure  
* Azure Kubernetes Service (AKS)  
* Prometheus  
* Grafana (self-hosted and Azure Managed)  
* Grafana Loki  
* cAdvisor  
* Azure CLI  
* Terraform

## **Project 3 (Final Capstone): End-to-End DevOps Deployment**

**Objective:** Apply all core DevOps skills acquired throughout the course to design, build, and deploy a production-ready microservices application using best practices in automation, orchestration, monitoring, and team collaboration.

**Description:** In this capstone project, students will work in teams to simulate a real-world DevOps environment. They will implement the full DevOps lifecycle—from infrastructure provisioning with Terraform and Ansible, to containerization with Docker, orchestration with Kubernetes, CI/CD automation with GitHub Actions, and performance monitoring using Prometheus and Grafana. Students can choose between AWS, Azure, or hybrid cloud deployments. Agile methodologies and scrum rituals will guide team collaboration, with responsibilities distributed across roles such as Scrum Master and developers. **This project consolidates and applies all major skills and tools from previous course units**, ensuring students demonstrate end-to-end proficiency in DevOps practices.

**Deliverables:**

* GitHub repository with:  
  * Infrastructure-as-Code files (Terraform, Ansible, CloudFormation, etc.)  
  * Dockerfiles and Kubernetes manifests  
  * GitHub Actions CI/CD pipelines  
* Deployed application running on Kubernetes (EKS/AKS)  
* Monitoring dashboards and alerting setup  
* Documentation covering architecture, CI/CD setup, security, and team processes  
* Team sprint board (Azure Boards, Jira, etc.) and recorded sprint rituals

**Tools:**

* All or most of the tools learned throughout the course.
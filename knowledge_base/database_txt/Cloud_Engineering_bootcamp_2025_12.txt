Course contents  
**Cloud Engineering Bootcamp**

**Table of contents**

 - [Course Duration](#course-duration)
 - [Course Overview](#course-overview)
 - [Learning Outcomes](#learning-outcomes)
 - [Course Details](#course-details)
   - [Unit 0: Pre-Work](#unit-0-pre-work)
   - [Unit 1: Cloud Foundations](#unit-1-cloud-foundations)
   - [Unit 2: Core Services](#unit-2-core-services)
   - [Unit 3: Networking & Single-Cloud Architecture](#unit-3-networking-single-cloud-architecture)
   - [Project 1: Foundational Cloud Deployment](#project-1-foundational-cloud-deployment)
   - [Unit 4: Infrastructure as Code](#unit-4-infrastructure-as-code)
   - [Unit 5: Automation](#unit-5-automation)
   - [Unit 6: Observability](#unit-6-observability)
   - [Project 2: Monitored & Optimized Cloud Platform](#project-2-monitored-optimized-cloud-platform)
   - [Unit 7: FinOps](#unit-7-finops)
   - [Unit 8: Security, Compliance](#unit-8-security-compliance)
   - [Unit 9: Capstone](#unit-9-capstone)
 - [Assessment](#assessment)
 - [Materials Provided](#materials-provided)
 - [Tools Needed](#tools-needed)

## **Course Duration** {#course-duration}

* **Total:** 360 hours + 40 hours prework  
* **Format:**   
  * Full-time, Monday–Friday (\~8h/day).  
  * **Delivery:** Instructor-led, live sessions with guided labs, team projects, mentoring, and code reviews; delivered on campus or remote, following Ironhack’s project-based pedagogy.  
* **Daily Flow:** Mornings focus on lecture \+ live demos \+ short labs; afternoons on project work, mentoring, and code reviews; Fridays include project presentations and feedback.

## **Course Overview** {#course-overview}

This program takes absolute beginners from foundations to job-ready cloud engineering. After completing the Pre-Work, students progress through carefully scaffolded units: IT & cloud fundamentals; core services and security across AWS; production-grade networking and single-cloud architecture; Infrastructure as Code with Terraform and automation via CI/CD and GitOps; observability and FinOps for reliability and cost control; and security & compliance for regulated environments. 

Throughout the course, learners use AI assistants (e.g., ChatGPT, GitHub Copilot) to accelerate troubleshooting, generate Terraform and configuration snippets, and improve documentation. The journey culminates in a capstone where teams design and present a secure, observable, cost-optimized multi-cloud platform with Terraform repos, pipelines, dashboards, and a compliance report—evidence of readiness for Junior Cloud Engineer / Junior DevOps roles.

## **Learning Outcomes** {#learning-outcomes}

By the end of the Cloud Engineering Bootcamp, students will be able to:

* **Operate confidently in AWS:** Use the command line to manage Linux systems, understand networking fundamentals, and work securely with remote servers. Navigate AWS console and command-line tools to provision and manage resources.  
* **Design and deploy cloud infrastructure:** Plan and build production-ready single- and multi-cloud architectures including compute, storage, networking, security, and identity management. Apply cost-awareness from the beginning of the design.  
* **Automate infrastructure with code:** Write and organize Terraform configurations, manage state remotely, create reusable modules, and integrate infrastructure changes into Git-based workflows. Use CI/CD pipelines to automate provisioning and configuration at scale.  
* **Implement observability and cost control:** Instrument systems with metrics, logs, and tracing using Prometheus, Grafana, and OpenTelemetry. Create dashboards and alerts to monitor reliability and performance. Analyze and optimize spend using FinOps principles and cloud cost tools.  
* **Secure and ensure compliance:** Apply security baselines (CIS, NIST, ISO 27001\) and use native cloud tools (AWS Config) to harden systems. Manage secrets and identity with Vault and Keycloak, and address compliance standards such as GDPR, SOC 2, HIPAA, and the EU AI Act.  
* **Use AI to accelerate cloud engineering workflows:** Leverage tools such as ChatGPT and GitHub Copilot to generate Terraform and Ansible code, debug CI/CD pipelines, explain unfamiliar services, document infrastructure, and automate compliance checks.  
* **Build a professional portfolio and prepare for certifications:** Complete weekly hands-on labs and projects plus a capstone multi-cloud platform to showcase job-ready skills. Be prepared to take industry certifications including AWS Certified Cloud Practitioner and HashiCorp Terraform Associate.  
* **Launch a career in Cloud Engineering / DevOps:** Graduate ready to apply for roles such as Junior Cloud Engineer, Junior DevOps Engineer, Cloud Support Engineer, Infrastructure Automation Engineer, and entry-level Site Reliability Engineer (SRE).  
* Be prepared to achieve industry-recognized certifications such as AWS Certified Cloud Practitioner and HashiCorp Terraform Associate through dedicated review and practice.

## **Course Details** {#course-details}

### **Unit 0: Pre-Work** {#unit-0-pre-work}

* **Duration:** Self-paced (40 hours completed before bootcamp start)  
* **Topics:**  
  * Computer & OS basics (filesystems, processes, users and permissions, package managers)  
  * Linux CLI navigation, file manipulation, SSH, basic shell scripting  
  * Networking fundamentals: IP, DNS, HTTP/HTTPS, ports, firewalls, troubleshooting tools (ping, curl)  
  * Cloud concepts: virtualization vs containers, shared responsibility model  
  * Version control with Git and GitHub (commits, branching, pull requests)  
  * Optional: simple Python scripting for automation  
* **Example Activities:**   
  * Guided terminal lab: navigating file systems, editing files, managing permissions  
  * SSH into a cloud VM and explore basic system monitoring commands  
  * Hands-on Git workflow: clone, branch, commit, open a pull request  
* **Outcome:** Students start the bootcamp confident with Linux, basic networking, Git collaboration, and cloud fundamentals so they can focus on higher-level concepts from week one.

### **Unit 1: Cloud Foundations** {#unit-1-cloud-foundations}

* **Duration:** Week 1 (40h)  
* **Topics:**  
  * Linux recap: users, permissions, SSH  
  * Networking recap: IP, DNS, HTTP  
  * Cloud fundamentals: AWS Free Tier, shared responsibility model  
  * Identity and Access Management (IAM) basics  
  * Cloud pricing and free tier usage  
* **Example Activities:**   
  * Guided lab: connect to a Linux VM via SSH and configure users & permissions  
  * Deploy a static website on Amazon S3 with IAM-based access control  
  * Estimate costs using AWS Pricing Calculator  
* **Outcome:** Students can confidently navigate the Linux CLI, connect to cloud servers, understand IAM and pricing basics, and deploy a simple workload to AWS.

### **Unit 2: Core Services** {#unit-2-core-services}

* **Duration:** Week 2 (40h)  
* **Topics:**  
  * Provisioning virtual machines (AWS EC2)  
  * Configuring cloud storage (S3)  
  * IAM roles and security policies  
  * Firewalls and security groups  
  * Cost estimation and budget alerts with provider tools  
* **Example Activities:**   
  * Lab: launch a VM, attach storage, configure IAM roles and security groups  
  * Workshop: compare pricing options with calculators and budgets  
  * Mini project: deploy a secure single-tier application across AWS  
* **Outcome:** Students can build secure, cost-aware workloads using core cloud services and apply IAM and firewall best practices across major providers.

### **Unit 3: Networking & Single-Cloud Architecture** {#unit-3-networking-single-cloud-architecture}

* **Duration**: Week 3 (40h)  
* **Topics**:  
  * Designing virtual private networks (VPCs / VNETs)  
  * Creating public and private subnets with routing tables and NAT gateways  
  * Domain Name System (DNS) and load balancers  
  * Securing network traffic with NACLs and security groups  
  * Introduction to hybrid connectivity (VPN, on-prem to cloud links)  
* **Example Activities**:  
  * Guided lab: create a VPC with public/private subnets and NAT gateway  
  * Configure and test a load balancer to serve a simple web app  
  * Exercise: design and diagram a secure network for a 3-tier application  
* **Outcome**: Students can design and implement secure cloud networks, route traffic effectively, and deploy a production-style 3-tier app inside a single cloud provider.


### **Project 1: Foundational Cloud Deployment** {#project-1-foundational-cloud-deployment}

* **Duration**: 2-3 days (Week 3\)  
* **Description:** Individual project where students design and deploy a secure 3-tier cloud application using a single provider (AWS). They will apply networking, IAM and cost control fundamentals to create a working system.  
* **Main Objectives:**  
  * Deploy a secure, networked 3-tier infrastructure.  
  * Implement IAM best practices and cost awareness.  
* **Deliverables:**  
  * Terraform or console-based deployment.  
  * Architecture diagram and cost estimate report.  
* **Expected Outcomes:** Students demonstrate their ability to deploy foundational infrastructure independently and explain how their design meets security and cost-efficiency standards.

### **Unit 4: Infrastructure as Code** {#unit-4-infrastructure-as-code}

* **Duration**: Week 4 (40h)  
* **Topics**:  
  * Terraform fundamentals: init, plan, apply  
  * Managing state (local vs remote backends)  
  * Creating reusable modules with variables and outputs  
  * Version control and code reviews for infrastructure  
* **Example Activities**:  
  * Lab: write Terraform code to provision a VPC and an EC2 instance  
  * Workshop: configure remote state storage and lock state changes  
  * Refactor: convert manually created infrastructure into Terraform modules  
* **Outcome**: Students can define infrastructure as code using Terraform, organize it into reusable modules, and safely manage shared state in a collaborative workflow.

### **Unit 5: Automation** {#unit-5-automation}

* **Duration**: Week 5 (40h)  
* **Topics**:  
  * CI/CD for infrastructure with GitHub Actions  
  * GitOps workflows: pull request-driven deployments  
  * Configuration management with Ansible and Helm  
  * Infrastructure testing with Terratest  
  * AI assistants (e.g., ChatGPT, GitHub Copilot) for code generation and debugging  
* **Example Activities**:  
  * Lab: create a CI/CD pipeline that plans and applies Terraform automatically  
  * Workshop: use Ansible to configure servers post-deployment  
  * Guided demo: use AI to generate Terraform snippets and troubleshoot pipeline errors  
* **Outcome**: Students can fully automate infrastructure deployment using CI/CD and GitOps, integrate testing and configuration management, and leverage AI to work faster and solve issues.

### **Unit 6: Observability** {#unit-6-observability}

* **Duration**: Week 6 (40h)  
* **Topics:**  
  * Observability fundamentals: metrics, logs and tracing  
  * OpenTelemetry instrumentation for apps  
  * Prometheus and Grafana for collection, visualization and alerting  
  * Cloud-native monitoring: AWS CloudWatch  
* **Example Activities**:  
  * Lab: instrument a sample application with OpenTelemetry  
  * Build dashboards and alerts in Grafana to monitor system health  
  * Guided demo: analyze and respond to simulated outages  
* **Outcome**: Students can design and implement observability for cloud systems, collect and visualize telemetry, and set up alerts to support reliable operations.

### **Project 2: Monitored & Optimized Cloud Platform** {#project-2-monitored-optimized-cloud-platform}

* **Duration**: 2-3 days (Week 6\)  
* **Description:** Group project (pairs or trios) to extend an existing infrastructure with observability, monitoring, and cost optimization features.  
* **Main Objectives:**  
  * Collect and visualize metrics, logs, and traces.  
  * Build Grafana dashboards and alerting systems.  
  * Apply FinOps practices to analyze and reduce cost.  
* **Deliverables:**  
  * Working observability stack (Prometheus/Grafana).  
  * Cost dashboard or optimization report.  
  * Project documentation (README \+ diagrams).  
* **Expected Outcomes:** Students can operate and optimize production-grade infrastructure using observability and FinOps techniques.

### **Unit 7: FinOps** {#unit-7-finops}

* **Duration**: Week 7 (40h)  
* **Project:**  
  * Cloud pricing models: on-demand, reserved, spot  
  * Budgeting, tagging and cost allocation strategies  
  * Cost analysis dashboards: AWS Cost Explorer  
  * Rightsizing and optimization planning  
* **Example Activities**:  
  * Audit the cost of an existing environment and identify savings  
  * Create a budgeting and tagging strategy for a sample workload  
  * Use AI to compare pricing models and propose optimization plans  
* **Outcome**: Students can analyze, forecast and control cloud spending, applying FinOps practices to build cost-efficient, business-aligned infrastructure.

### **Unit 8: Security, Compliance** {#unit-8-security-compliance}

* **Duration**: Week 8 (40h)  
* **Topics**:  
  * Security frameworks: CIS, NIST, ISO 27001  
  * Cloud-native security tools: AWS Config  
  * Intrusion detection with Wazuh  
  * Secrets and identity management with Vault and Keycloak  
  * Compliance standards: GDPR, SOC 2, HIPAA, EU AI Act  
* **Example Activities**:  
  * Lab: run CIS benchmark scans against a cloud account  
  * Workshop: configure Vault to manage sensitive secrets  
  * Guided review: analyze a compliance checklist for a sample workload  
* **Outcome**: Students can secure and harden cloud infrastructure, implement baseline compliance controls and prepare environments for regulated industries.

### **Unit 9: Capstone** {#unit-9-capstone}

* **Duration**: Week 9 (40h)  
* **Topics**:  
  * Designing a multi-cloud architecture integrating compute, storage, networking and security  
  * Automating deployment with Terraform and CI/CD pipelines  
  * Adding observability, cost optimization and compliance controls  
  * Preparing professional documentation and architecture presentation  
* **Example Activities**:  
  * Team project: build and present a secure, cost-optimized, observable multi-cloud platform  
  * Guided practice: prepare for AWS Cloud Practitioner & Terraform Associate exams  
  * Final presentation: defend design and operational decisions to instructors and peers  
* **Outcome**: Students integrate all acquired skills to design and deliver a production-ready multi-cloud solution, showcase their portfolio and demonstrate readiness for junior cloud engineering and DevOps roles.

## **Assessment** {#assessment}

Student progress is evaluated continuously to ensure readiness for real-world cloud engineering work.

Each week includes guided labs and mini-projects that reinforce new skills. Instructors review and provide feedback on infrastructure code, cloud configurations, and CI/CD pipelines.

Every Friday ends with a project presentation and demo, where students explain their architecture and decisions.

Student progress is evaluated continuously through projects, labs, and participation:

* Project 1 \- Foundational Cloud Deployment: **15%**  
* Project 2 \- Monitored & Optimized Platform: **25%**  
* Capstone Project \- Multi-Cloud Infrastructure: **40%**  
* Labs, Exercises, and Participation: **20%**

This continuous assessment approach mirrors industry workflows, emphasizing both technical output and the ability to explain and defend architectural choices.

## **Materials Provided** {#materials-provided}

**For students:**

* Instructor-curated slides and notes that align with each week’s topics and labs.  
* Step-by-step lab guides for cloud setup, Terraform workflows, CI/CD pipelines, and observability tools.  
* Code templates and starter repositories hosted on GitHub to accelerate hands-on work.  
* Practice exam resources for AWS Certified Cloud Practitioner and HashiCorp Terraform Associate (sample questions, study checklists).  
* Reference sheets with essential Linux, networking, Terraform and cloud CLI commands

**For instructors:**

* Lesson plans with learning objectives and timing breakdown  
* Lab solutions  
* Project grading rubrics  
* Discussion prompts and case studies for facilitating group learning and real-world application

## **Tools Needed** {#tools-needed}

During the program, students will work with a modern cloud engineering toolset, mirroring professional environments:

* **Cloud Providers:** Amazon Web Services (AWS)  
* **Infrastructure as Code:** Terraform (CLI), GitHub for version control and pull-request reviews  
* **Automation & DevOps:** GitHub Actions for CI/CD, Ansible and Helm for configuration management  
* **Observability:** Prometheus, Grafana, OpenTelemetry; cloud-native tools (AWS CloudWatch)  
* **Security & Compliance:** Vault for secrets, Keycloak for IAM, AWS Config  
* **AI Tools:** ChatGPT and GitHub Copilot to assist with Terraform generation, troubleshooting and documentation  
* **Developer Environment:** Visual Studio Code (or equivalent IDE), terminal/SSH client, modern browser
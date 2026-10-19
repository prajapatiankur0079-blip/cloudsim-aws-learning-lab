# CloudSim AWS Learning Lab

A local, interactive cloud infrastructure simulator built with Python, Flask, and SQLite. CloudSim helps beginners explore AWS concepts and practice common cloud operations without creating real AWS resources or incurring AWS charges.

## Features

- **Learning Hub:** Explore cloud services and their core concepts.
- **EC2 Lab:** Simulate virtual instance creation, start, stop, and termination.
- **S3 Lab:** Practice bucket management and simulated object metadata operations.
- **VPC & Subnet Lab:** Explore virtual networks, subnet CIDR ranges, and overlap validation.
- **Internet Gateway & Routing Lab:** Practice gateway attachment, route tables, and public subnet routing.
- **NAT Gateway Lab:** Explore NAT concepts and private subnet connectivity simulations.
- **Security Group Lab:** Learn inbound and outbound traffic rules, ports, protocols, and traffic decisions.
- **Route 53 DNS Lab:** Practice hosted zones, A/CNAME/MX/TXT records, input validation, and DNS lookups.
- **Automated Tests:** Run regression tests for core pages, cloud operations, validation, and networking scenarios.

## Technology Stack

- Python
- Flask
- SQLite
- HTML and CSS
- pytest
- Git and GitHub

## Getting Started

### Prerequisites

- Python 3
- Git
- A web browser

### 1. Clone the repository

```bash
git clone https://github.com/prajapatiankur0079-blip/cloudsim-aws-learning-lab.git
cd cloudsim-aws-learning-lab
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install Flask pytest
```

### 4. Start CloudSim

```bash
python app.py
```

Open http://127.0.0.1:5000 in your browser if Flask reports that address.

## Run Automated Tests

From the project directory, with the virtual environment activated:

```bash
python -m pytest -v tests/test_routes.py
```

The latest full local test run passed **173 tests**. The count may change as tests are added. It covers:

- Main learning and service page responses.
- EC2 instance lifecycle operations.
- S3 bucket and object metadata operations, including validation.
- VPC creation and overlapping subnet rejection.
- Security Group traffic rule decisions.
- Route 53 hosted zone creation, DNS record lookup, and validation.
- NAT Gateway and private subnet connectivity scenarios.
- Internet Gateway attachment, detachment, and public routing.
- Rejection of invalid NAT route targets and invalid destination IPs.

Tests use an isolated temporary SQLite database so test operations do not modify the normal local project database.

## Learning Objectives

- Understand foundational cloud computing concepts.
- Practice VPC, subnet, and CIDR validation.
- Learn routing, Internet Gateway, and NAT Gateway concepts.
- Explore network traffic rules with Security Groups.
- Understand DNS records and hosted zone management.
- Practice Python, Flask, SQLite, testing, and Git workflows.

## Important Limitations

- CloudSim is an educational simulator, not the AWS Management Console.
- Cloud resources and networking operations are simulated locally.
- It does not create real EC2 instances, S3 buckets, VPCs, gateways, Security Groups, or Route 53 hosted zones.
- Simulated connectivity results do not prove real network connectivity.
- The project has not been presented as a production-ready cloud platform.

## Future Improvements

- Add application screenshots and a demo.
- Document the application architecture.
- Continue expanding automated tests and input validation.
- Improve setup documentation and dependency management.
- Explore safe deployment options.

## Author

Created as a hands-on cloud infrastructure learning project.

## Repository

[CloudSim AWS Learning Lab on GitHub](https://github.com/prajapatiankur0079-blip/cloudsim-aws-learning-lab)

## Additional Labs

- **IAM Lab:** Users, groups, roles, policies, memberships and policy simulation.
- **Additional service simulators:** Lambda, RDS, DynamoDB, EBS, CloudFront, API Gateway, CloudWatch, CloudTrail, CloudFormation, SQS, SNS, ECS, EKS, EventBridge, KMS, EFS, CodePipeline and Cost Management.
- These additional services use a generic local simulation framework; they do not reproduce every AWS feature.

## Run Tests

```bash
python -m pytest -q
```

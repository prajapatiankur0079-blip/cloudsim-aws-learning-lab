# CloudSim AWS Learning Lab

An interactive cloud infrastructure learning simulator built with Python, Flask, and SQLite. It helps beginners practice AWS concepts in a local environment.

## Features

- **VPC Lab:** Practice VPC and CIDR concepts.
- **Subnet Lab:** Create simulated subnets and validate CIDR ranges and overlaps.
- **EC2 Lab:** Learn basic virtual server management concepts.
- **Routing and NAT Lab:** Explore route tables, routing, and NAT concepts.
- **S3 Lab:** Practice simulated object storage concepts.
- **Security Group Lab:** Understand inbound and outbound traffic rules, ports, and protocols.
- **Route 53 DNS Lab:** Create simulated hosted zones, manage A/CNAME/MX/TXT records, validate inputs, and look up DNS records.

## Tech Stack

- Python
- Flask
- SQLite
- HTML and CSS
- Git and GitHub

## Installation

### Prerequisites

- Python 3
- Git
- A web browser

### 1. Clone the repository

    git clone https://github.com/prajapatiankur0079-blip/cloudsim-aws-learning-lab.git
    cd cloudsim-aws-learning-lab

### 2. Create and activate a virtual environment

    python3 -m venv venv
    source venv/bin/activate

### 3. Install dependencies

    pip install Flask pytest

### 4. Run the application

    python app.py

Open http://127.0.0.1:5000 in your browser if Flask reports that address.

## Learning Objectives

- Understand cloud networking fundamentals.
- Practice VPC and subnet CIDR validation.
- Explore routing, NAT, and traffic control.
- Learn basic DNS record management.
- Understand EC2 and S3 concepts.
- Gain practical experience with Python, Flask, SQLite, and Git.

## Important Notes

- This is a local educational simulator, not the actual AWS cloud.
- Resources and operations are simulated locally.
- The Route 53 lab does not create real AWS hosted zones or DNS records.
- Never commit passwords, access tokens, private keys, or sensitive credentials.
- Keep local databases and environment-specific files out of the public repository.

## Automated Tests

The project includes pytest tests for page loading and core EC2/S3 operations.

Run the tests from the project directory with the virtual environment activated:

    python -m pytest -v tests/test_routes.py

The tests use a temporary SQLite database so test operations remain isolated from the local project database.

Current coverage includes:
- Main learning and service pages load successfully.
- EC2 instance creation, stopping, starting, and termination.
- S3 bucket creation and duplicate/invalid bucket validation.
- S3 object metadata creation.

## Future Improvements

- Add screenshots and a demo.
- Expand automated coverage for VPC, Security Groups, and Route 53 operations.
- Improve validation and error handling.
- Explore deployment options.

## Author

Created as a hands-on cloud infrastructure learning project.

## Repository

https://github.com/prajapatiankur0079-blip/cloudsim-aws-learning-lab

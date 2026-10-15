# CloudSim Architecture
## Overview

CloudSim is a local educational cloud infrastructure simulator built with
Python, Flask, and SQLite. It helps beginners explore cloud concepts and
practice selected operations without creating real AWS resources.

## Main Components

- app.py: Main Flask application, home page, learning center, EC2 and S3.
- vpc_lab.py: VPC, subnet, gateway, routing and connectivity simulations.
- security_group_lab.py: Security Group rules and traffic simulation.
- route53_lab.py: Hosted zones, DNS records and simulated lookups.
- templates/: HTML pages for the web interface.
- static/style.css: Web interface styling.
- tests/test_routes.py: Automated regression tests.
- cloudlab.db: Local SQLite database.

## Request Flow

1. The user opens a page or submits a form in the browser.
2. Flask routes the request to the relevant application function or lab blueprint.
3. The application validates inputs and performs a simulated operation.
4. SQLite stores or retrieves local data where required.
5. Flask renders a page or redirects the user with a status message.

## Database Initialization

At application startup, app.py initializes the main application database
and the VPC, NAT Gateway, Security Group, and Route 53 lab databases.

## Automated Testing

Run the test suite from the project directory with the virtual environment active:

    python -m pytest -v tests/test_routes.py

The verified test suite currently contains 25 collected tests.

## Limitations

- CloudSim is an educational simulator, not the AWS Management Console.
- It does not create real AWS resources.
- Networking and DNS outcomes are simulated locally.
- It is intended for learning and practice, not production infrastructure management.

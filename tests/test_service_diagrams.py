from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

LESSONS_DIR = Path("static/images/lessons")

SERVICES = [
    "s3", "lambda", "vpc", "security-groups", "iam", "rds",
    "dynamo", "ebs", "route53", "cloudfront", "api", "cloudwatch",
    "cloudtrail", "cfn", "sqs", "sns", "ecs", "eks", "events",
    "kms", "efs", "pipeline", "cost",
]

DIAGRAM_TYPES = [
    "architecture",
    "components",
    "workflow",
    "troubleshooting",
    "usecase",
]


def parse_svg(path):
    assert path.is_file(), f"Missing SVG: {path}"
    root = ET.parse(path).getroot()
    assert root.tag.endswith("svg"), f"Invalid SVG root: {path}"
    return root


def test_all_lesson_svgs_are_valid_xml():
    files = sorted(LESSONS_DIR.glob("*.svg"))
    assert files, "No SVG files found"

    for path in files:
        parse_svg(path)


@pytest.mark.parametrize("service", SERVICES)
@pytest.mark.parametrize("diagram_type", DIAGRAM_TYPES)
def test_service_diagram_exists_and_has_viewbox(service, diagram_type):
    path = LESSONS_DIR / f"{service}-{diagram_type}.svg"
    root = parse_svg(path)

    assert root.attrib.get("viewBox"), f"Missing viewBox: {path}"
    assert root.attrib.get("width"), f"Missing width: {path}"
    assert root.attrib.get("height"), f"Missing height: {path}"


def test_ec2_original_diagrams_are_present():
    expected = [
        "ec2-architecture.svg",
        "ec2-aws-icon.svg",
        "ec2-components.svg",
        "ec2-lifecycle.svg",
        "ec2-request-path.svg",
        "ec2-scaling.svg",
        "ec2-security.svg",
        "ec2-storage.svg",
        "ec2-troubleshooting.svg",
        "ec2-usecase.svg",
        "ec2-workflow.svg",
    ]

    for filename in expected:
        parse_svg(LESSONS_DIR / filename)

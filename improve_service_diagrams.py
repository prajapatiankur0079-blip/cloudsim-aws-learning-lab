from pathlib import Path
from html import escape
import re
import sys

from service_lessons import SERVICE_LESSONS

OUT = Path("static/images/lessons")
OUT.mkdir(parents=True, exist_ok=True)

# Real service-specific architecture components and relationships.
ARCH = {
    "s3": ["Web / App", "IAM + Bucket Policy", "S3 Bucket", "Objects + Versions"],
    "lambda": ["Event Source", "Lambda Trigger", "Function + Role", "CloudWatch Logs"],
    "vpc": ["Internet", "Internet Gateway", "Public Subnet", "Private Subnet"],
    "security-groups": ["Client", "Inbound Rule", "Resource ENI", "Allowed Traffic"],
    "iam": ["User / Workload", "Assume Role", "Policy Evaluation", "AWS Resource"],
    "rds": ["Application", "DB Subnet Group", "RDS Endpoint", "SQL Database"],
    "dynamo": ["Application", "API Request", "DynamoDB Table", "Item by Key"],
    "ebs": ["EC2 Instance", "Block Device", "EBS Volume", "Snapshot Backup"],
    "route53": ["Domain Query", "DNS Resolver", "Hosted Zone Record", "Endpoint"],
    "cloudfront": ["Viewer", "Edge Location", "Cache Lookup", "Origin on Cache Miss"],
    "api": ["Client", "API Gateway Route", "Authorizer / Validation", "Lambda Integration"],
    "cloudwatch": ["AWS Resource", "Metrics + Logs", "Alarm Evaluation", "Notification"],
    "cloudtrail": ["AWS API Call", "CloudTrail Event", "Event History / S3", "Audit Investigation"],
    "cfn": ["Template", "Change Set", "CloudFormation Stack", "Provisioned Resources"],
    "sqs": ["Producer", "SQS Queue", "Worker Consumer", "Delete on Success"],
    "sns": ["Publisher", "SNS Topic", "Subscription", "Email / HTTPS / SQS"],
    "ecs": ["Container Image", "Task Definition", "ECS Service", "Running Tasks"],
    "eks": ["kubectl / CI", "Kubernetes API", "Scheduler", "Pods on Worker Nodes"],
    "events": ["Event Producer", "Event Bus", "Matching Rule", "Target Service"],
    "kms": ["Application / AWS", "IAM + Key Policy", "KMS Key Operation", "Encrypted Data"],
    "efs": ["EC2 / Compute A", "Mount Target", "Shared EFS Filesystem", "EC2 / Compute B"],
    "pipeline": ["Source Change", "Source Stage", "Build + Test", "Deploy Stage"],
    "cost": ["Usage Records", "Cost Explorer / Budget", "Threshold Check", "Budget Alert"],
}

PALETTE = {
    "s3": "#38bdf8", "lambda": "#a78bfa", "vpc": "#34d399",
    "security-groups": "#f59e0b", "iam": "#fb7185", "rds": "#60a5fa",
    "dynamo": "#fbbf24", "ebs": "#c084fc", "route53": "#2dd4bf",
    "cloudfront": "#818cf8", "api": "#22d3ee", "cloudwatch": "#f97316",
    "cloudtrail": "#f472b6", "cfn": "#a3e635", "sqs": "#38bdf8",
    "sns": "#fb923c", "ecs": "#34d399", "eks": "#c084fc",
    "events": "#facc15", "kms": "#f87171", "efs": "#2dd4bf",
    "pipeline": "#60a5fa", "cost": "#a3e635",
}

def wrap(text, limit=23):
    words = str(text).split()
    lines, current = [], ""
    for word in words:
        if len(current) + len(word) + (1 if current else 0) <= limit:
            current = (current + " " + word).strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines[:3] or [""]

def txt(x, y, value, size=15, color="#e5edf8", weight=400, anchor="start",
        max_chars=25):
    lines = wrap(value, max_chars)
    spans = []
    line_gap = max(15, round(size * 1.25))
    for i, line in enumerate(lines):
        dy = 0 if i == 0 else line_gap
        spans.append(
            f'<tspan x="{x}" dy="{dy}">{escape(line)}</tspan>'
        )
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
        f'font-weight="{weight}" text-anchor="{anchor}">'
        + "".join(spans) + "</text>"
    )

def svg_start(title, subtitle, accent):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="600"
 viewBox="0 0 1100 600" role="img">
 <defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
   <stop offset="0" stop-color="#0b1424"/>
   <stop offset="1" stop-color="#101f35"/>
  </linearGradient>
  <marker id="arrow" markerWidth="9" markerHeight="9" refX="7" refY="3"
   orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="{accent}"/></marker>
 </defs>
 <rect width="1100" height="600" rx="22" fill="url(#bg)"/>
 <rect x="30" y="28" width="7" height="62" rx="3" fill="{accent}"/>
 {txt(55, 54, title, 24, "#f8fafc", 700, max_chars=65)}
 {txt(55, 84, subtitle, 12, "#a9bbd2", max_chars=100)}
 <line x1="35" y1="112" x2="1065" y2="112" stroke="#293b53"/>
'''

def card(x, y, w, h, title, detail, accent, number=None):
    out = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="13" '
        f'fill="#111e31" stroke="{accent}" stroke-width="1.7"/>',
        f'<rect x="{x}" y="{y}" width="5" height="{h}" rx="2" fill="{accent}"/>'
    ]
    if number is not None:
        out.append(
            f'<circle cx="{x+24}" cy="{y+25}" r="12" fill="{accent}"/>'
            f'<text x="{x+24}" y="{y+30}" text-anchor="middle" '
            f'font-size="12" font-weight="700" fill="#07111f">{number}</text>'
        )
        title_limit = max(14, int((w - 70) / 7))
        detail_limit = max(20, int((w - 36) / 7))
        out.append(txt(x+45, y+30, title, 16, "#f8fafc", 700,
                       max_chars=title_limit))
        out.append(txt(x+18, y+61, detail, 13, "#b8c8dc",
                       max_chars=detail_limit))
    else:
        title_limit = max(18, int((w - 34) / 7))
        detail_limit = max(18, int((w - 34) / 7))
        out.append(txt(x+17, y+30, title, 16, "#f8fafc", 700,
                       max_chars=title_limit))
        out.append(txt(x+17, y+59, detail, 13, "#b8c8dc",
                       max_chars=detail_limit))
    return "\n".join(out)

def arrow(x1, y1, x2, y2, accent, label=None):
    s = (f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" '
         f'stroke="{accent}" stroke-width="2.5" marker-end="url(#arrow)"/>')
    if label:
        s += txt((x1+x2)/2, (y1+y2)/2-9, label, 11, accent, 700, "middle")
    return s

def footer(slug, accent):
    return (
        f'<line x1="35" y1="548" x2="1065" y2="548" stroke="#293b53"/>'
        f'{txt(38, 575, "CLOUDSIM  /  CONCEPTUAL AWS LEARNING DIAGRAM", 11, "#8295ae", max_chars=90)}'
        f'{txt(1060, 575, slug.upper().replace("-", " "), 11, accent, 700, "end", max_chars=40)}'
        '</svg>'
    )

def save(slug, kind, title, subtitle, body, accent):
    path = OUT / f"{slug}-{kind}.svg"
    path.write_text(
        svg_start(title, subtitle, accent) + body + footer(slug, accent),
        encoding="utf-8"
    )

def create_diagrams(slug, lesson):
    if slug == "ec2":
        return  # Preserve the five hand-designed EC2 diagrams.

    accent = PALETTE[slug]
    arch = ARCH[slug]
    components = lesson["components"]
    workflow = lesson["workflow"]

    # 1. Architecture: named AWS components connected in service-specific order.
    body = (
        '<rect x="50" y="145" width="1000" height="285" rx="18" '
        'fill="#0b1728" stroke="#34465e" stroke-dasharray="7 6"/>'
        + txt(72, 174, "SERVICE BOUNDARY / REQUEST PATH", 12, accent, 700)
    )
    xs = [65, 325, 585, 845]
    for i, label in enumerate(arch):
        body += card(xs[i], 230, 190, 105, label,
                     ["Entry point", "Access / routing", "Core service", "Output / result"][i],
                     accent)
        if i < 3:
            body += arrow(xs[i]+190, 282, xs[i+1]-10, 282, accent)
    body += txt(75, 385, "Security, permissions and monitoring must match the workload.", 14)
    save(slug, "architecture", f"{lesson['name']} | Architecture",
         "Service-specific components and their relationship", body, accent)

    # 2. Components: two-column component map, not another horizontal flow.
    body = ""
    for i, item in enumerate(components[:8]):
        col, row = i % 2, i // 2
        x, y = 70 + col*500, 145 + row*91
        body += card(x, y, 440, 70, item,
                     f"Configuration area {i+1} · review purpose and access", accent,
                     number=i+1)
    body += txt(75, 525, "Know what each component controls before changing a configuration.", 14)
    save(slug, "components", f"{lesson['name']} | Component Map",
         "Key building blocks to recognise in architecture and operations", body, accent)

    # 3. Workflow: numbered operational sequence.
    body = ""
    n = min(len(workflow), 5)
    start_x, gap, w = 65, 205, 175
    for i, step in enumerate(workflow[:n]):
        x = start_x + i*gap
        body += card(x, 235, w, 120, step, f"Stage {i+1} · verify before proceeding",
                     accent, number=i+1)
        if i < n-1:
            body += arrow(x+w, 294, x+gap-10, 294, accent)
    body += txt(70, 425, "Operational sequence", 18, "#f8fafc", 700)
    body += txt(70, 457, "Validate the result at each stage; use logs and events to investigate failures.", 14)
    save(slug, "workflow", f"{lesson['name']} | Workflow",
         "Follow the service's real operating sequence", body, accent)

    # 4. Troubleshooting: diagnostic path with a clear check / fix sequence.
    checks = [
        ("1 · Observe", "Capture the exact error, time and affected resource."),
        ("2 · Inspect", lesson["issue"]),
        ("3 · Correct", "Change one likely cause; avoid broad permission changes."),
        ("4 · Verify", "Repeat the operation and confirm logs or metrics are healthy."),
    ]
    body = ""
    for i, (heading, detail) in enumerate(checks):
        y = 145 + i*91
        body += card(95, y, 910, 68, heading, detail, accent, number=i+1)
        if i < 3:
            body += arrow(550, y+68, 550, y+87, accent)
    save(slug, "troubleshooting", f"{lesson['name']} | Troubleshooting",
         "A safe diagnostic path from symptom to verified fix", body, accent)

    # 5. Use case: grounded in the service's stated real-world example.
    stages = arch
    body = (
        '<rect x="55" y="140" width="990" height="86" rx="13" '
        f'fill="#111e31" stroke="{accent}" stroke-width="1.6"/>'
        + txt(78, 169, "REAL-WORLD SCENARIO", 12, accent, 700)
        + txt(78, 201, lesson["example"], 16, "#f8fafc", 700)
    )
    for i, label in enumerate(stages):
        x = 65 + i*260
        body += card(x, 300, 205, 100, label,
                     ["Initiate", "Authorise / route", "Process", "Deliver / observe"][i],
                     accent, number=i+1)
        if i < 3:
            body += arrow(x+205, 350, x+250, 350, accent)
    body += txt(72, 465, "Production review", 17, "#f8fafc", 700)
    body += txt(72, 497, "Check least privilege, failure handling, monitoring and cost.", 14)
    save(slug, "usecase", f"{lesson['name']} | Real-World Use Case",
         "Connect the service to a practical cloud engineering scenario", body, accent)

selected = set(sys.argv[1:])
unknown = selected - set(SERVICE_LESSONS)
if unknown:
    raise SystemExit("Unknown service slug(s): " + ", ".join(sorted(unknown)))

processed = []
for slug, lesson in SERVICE_LESSONS.items():
    if selected and slug not in selected:
        continue
    create_diagrams(slug, lesson)
    if slug != "ec2":
        processed.append(slug)

print("Services processed:", ", ".join(processed) if processed else "(none)")
print("EC2 originals are preserved.")
print("SVG files available:", len(list(OUT.glob("*.svg"))))

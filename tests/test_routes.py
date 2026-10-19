import sqlite3
import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Har test ke liye alag temporary database.
    db_path = str(tmp_path / "test_cloudlab.db")
    original_connect = sqlite3.connect

    # App import hote waqt bhi real database ki jagah
    # temporary database hi use ho.
    def isolated_connect(database, *args, **kwargs):
        return original_connect(db_path, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", isolated_connect)

    import app as cloudsim_app
    import vpc_lab
    import security_group_lab
    import route53_lab
    import iam_lab
    import extra_services_lab

    # Sabhi modules ko ek hi temporary database par set karo.
    monkeypatch.setattr(cloudsim_app, "DB", db_path)
    monkeypatch.setattr(vpc_lab, "DB", db_path)
    monkeypatch.setattr(security_group_lab, "DB", db_path)
    monkeypatch.setattr(route53_lab, "DB", db_path)
    monkeypatch.setattr(iam_lab, "DB", db_path)
    monkeypatch.setattr(extra_services_lab, "DB", db_path)

    # Temporary database mein tables initialize karo.
    cloudsim_app.init_db()
    vpc_lab.init_vpc_db()
    vpc_lab.init_nat_db()
    security_group_lab.init_security_group_db()
    route53_lab.init_route53_db()
    iam_lab.init_iam_db()
    extra_services_lab.init_extra_services_db()

    cloudsim_app.app.config.update(TESTING=True)

    with cloudsim_app.app.test_client() as test_client:
        yield test_client


@pytest.mark.parametrize("path", [
    "/",
    "/learning",
    "/practice/ec2",
    "/practice/s3",
    "/practice/vpc/",
    "/practice/security-groups/",
    "/practice/iam/",
    "/practice/route53/",
    "/practice/route53/lookup",
])
def test_pages_load(client, path):
    response = client.get(path, follow_redirects=True)
    assert response.status_code == 200, (
        f"{path} returned HTTP {response.status_code}"
    )


def test_ec2_create_instance(client):
    response = client.post(
        "/create",
        data={
            "name": "pytest-instance",
            "image": "Ubuntu Server 24.04",
            "instance_type": "t3.micro",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    import app as cloudsim_app
    conn = cloudsim_app.get_db()
    instance = conn.execute(
        "SELECT * FROM instances WHERE name = ?",
        ("pytest-instance",),
    ).fetchone()
    conn.close()

    assert instance is not None
    assert instance["state"] == "running"


def test_ec2_stop_and_start_instance(client):
    import app as cloudsim_app

    client.post("/create", data={"name": "pytest-state-check"})

    conn = cloudsim_app.get_db()
    instance = conn.execute(
        "SELECT id FROM instances WHERE name = ?",
        ("pytest-state-check",),
    ).fetchone()
    conn.close()
    assert instance is not None

    instance_id = instance["id"]

    stopped = client.post(
        f"/instance/{instance_id}/stop",
        follow_redirects=True,
    )
    assert stopped.status_code == 200

    conn = cloudsim_app.get_db()
    state = conn.execute(
        "SELECT state FROM instances WHERE id = ?",
        (instance_id,),
    ).fetchone()["state"]
    conn.close()
    assert state == "stopped"

    started = client.post(
        f"/instance/{instance_id}/start",
        follow_redirects=True,
    )
    assert started.status_code == 200

    conn = cloudsim_app.get_db()
    state = conn.execute(
        "SELECT state FROM instances WHERE id = ?",
        (instance_id,),
    ).fetchone()["state"]
    conn.close()
    assert state == "running"


def test_s3_create_bucket(client):
    response = client.post(
        "/s3/bucket/create",
        data={"name": "pytest-demo-bucket", "region": "ap-south-1"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    import app as cloudsim_app
    conn = cloudsim_app.get_db()
    bucket = conn.execute(
        "SELECT * FROM s3_buckets WHERE name = ?",
        ("pytest-demo-bucket",),
    ).fetchone()
    conn.close()

    assert bucket is not None
    assert bucket["region"] == "ap-south-1"


def test_s3_add_object_metadata(client):
    import app as cloudsim_app

    client.post(
        "/s3/bucket/create",
        data={"name": "pytest-object-bucket", "region": "ap-south-1"},
    )

    conn = cloudsim_app.get_db()
    bucket = conn.execute(
        "SELECT id FROM s3_buckets WHERE name = ?",
        ("pytest-object-bucket",),
    ).fetchone()
    conn.close()
    assert bucket is not None

    response = client.post(
        "/s3/object/upload",
        data={
            "bucket_id": str(bucket["id"]),
            "name": "sample.txt",
            "content_type": "text/plain",
            "size_kb": "12",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    conn = cloudsim_app.get_db()
    obj = conn.execute(
        "SELECT * FROM s3_objects WHERE bucket_id = ? AND name = ?",
        (bucket["id"], "sample.txt"),
    ).fetchone()
    conn.close()

    assert obj is not None
    assert obj["size_kb"] == 12
    assert obj["content_type"] == "text/plain"


def test_ec2_create_instance(client):
    response = client.post(
        "/create",
        data={
            "name": "pytest-instance",
            "image": "Ubuntu Server 24.04",
            "instance_type": "t3.micro",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    import app as cloudsim_app
    conn = cloudsim_app.get_db()
    instance = conn.execute(
        "SELECT * FROM instances WHERE name = ?",
        ("pytest-instance",),
    ).fetchone()
    conn.close()

    assert instance is not None
    assert instance["state"] == "running"


def test_ec2_stop_and_start_instance(client):
    import app as cloudsim_app

    client.post("/create", data={"name": "pytest-state-check"})

    conn = cloudsim_app.get_db()
    instance = conn.execute(
        "SELECT id FROM instances WHERE name = ?",
        ("pytest-state-check",),
    ).fetchone()
    conn.close()
    assert instance is not None

    instance_id = instance["id"]

    stopped = client.post(
        f"/instance/{instance_id}/stop",
        follow_redirects=True,
    )
    assert stopped.status_code == 200

    conn = cloudsim_app.get_db()
    state = conn.execute(
        "SELECT state FROM instances WHERE id = ?",
        (instance_id,),
    ).fetchone()["state"]
    conn.close()
    assert state == "stopped"

    started = client.post(
        f"/instance/{instance_id}/start",
        follow_redirects=True,
    )
    assert started.status_code == 200

    conn = cloudsim_app.get_db()
    state = conn.execute(
        "SELECT state FROM instances WHERE id = ?",
        (instance_id,),
    ).fetchone()["state"]
    conn.close()
    assert state == "running"


def test_s3_create_bucket(client):
    response = client.post(
        "/s3/bucket/create",
        data={"name": "pytest-demo-bucket", "region": "ap-south-1"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    import app as cloudsim_app
    conn = cloudsim_app.get_db()
    bucket = conn.execute(
        "SELECT * FROM s3_buckets WHERE name = ?",
        ("pytest-demo-bucket",),
    ).fetchone()
    conn.close()

    assert bucket is not None
    assert bucket["region"] == "ap-south-1"


def test_s3_add_object_metadata(client):
    import app as cloudsim_app

    client.post(
        "/s3/bucket/create",
        data={"name": "pytest-object-bucket", "region": "ap-south-1"},
    )

    conn = cloudsim_app.get_db()
    bucket = conn.execute(
        "SELECT id FROM s3_buckets WHERE name = ?",
        ("pytest-object-bucket",),
    ).fetchone()
    conn.close()
    assert bucket is not None

    response = client.post(
        "/s3/object/upload",
        data={
            "bucket_id": str(bucket["id"]),
            "name": "sample.txt",
            "content_type": "text/plain",
            "size_kb": "12",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    conn = cloudsim_app.get_db()
    obj = conn.execute(
        "SELECT * FROM s3_objects WHERE bucket_id = ? AND name = ?",
        (bucket["id"], "sample.txt"),
    ).fetchone()
    conn.close()

    assert obj is not None
    assert obj["size_kb"] == 12
    assert obj["content_type"] == "text/plain"


def test_ec2_terminate_instance(client):
    import app as cloudsim_app

    client.post("/create", data={"name": "pytest-terminate"})

    conn = cloudsim_app.get_db()
    instance = conn.execute(
        "SELECT id FROM instances WHERE name = ?",
        ("pytest-terminate",),
    ).fetchone()
    conn.close()
    assert instance is not None

    response = client.post(
        f"/instance/{instance['id']}/terminate",
        follow_redirects=True,
    )
    assert response.status_code == 200

    conn = cloudsim_app.get_db()
    remaining = conn.execute(
        "SELECT id FROM instances WHERE id = ?",
        (instance["id"],),
    ).fetchone()
    conn.close()

    assert remaining is None


def test_s3_rejects_invalid_bucket_name(client):
    response = client.post(
        "/s3/bucket/create",
        data={"name": "Invalid_Bucket_Name"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    import app as cloudsim_app
    conn = cloudsim_app.get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM s3_buckets"
    ).fetchone()[0]
    conn.close()

    assert count == 0


def test_s3_duplicate_bucket_is_rejected(client):
    import app as cloudsim_app

    data = {
        "name": "pytest-duplicate-bucket",
        "region": "ap-south-1",
    }

    first = client.post(
        "/s3/bucket/create", data=data, follow_redirects=True
    )
    second = client.post(
        "/s3/bucket/create", data=data, follow_redirects=True
    )

    assert first.status_code == 200
    assert second.status_code == 200

    conn = cloudsim_app.get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM s3_buckets WHERE name = ?",
        ("pytest-duplicate-bucket",),
    ).fetchone()[0]
    conn.close()

    assert count == 1


def test_vpc_creation_and_overlapping_subnet_rejection(client):
    import vpc_lab

    response = client.post(
        "/practice/vpc/create",
        data={"name": "Test VPC", "cidr": "10.0.0.0/16"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    conn = vpc_lab.db()
    vpc = conn.execute(
        "SELECT id FROM vpcs WHERE name = ?", ("Test VPC",)
    ).fetchone()
    conn.close()
    assert vpc is not None

    response = client.post(
        "/practice/vpc/subnet/create",
        data={
            "vpc_id": str(vpc["id"]),
            "name": "Public Subnet",
            "cidr": "10.0.1.0/24",
            "subnet_type": "public",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    response = client.post(
        "/practice/vpc/subnet/create",
        data={
            "vpc_id": str(vpc["id"]),
            "name": "Overlapping Subnet",
            "cidr": "10.0.1.128/25",
            "subnet_type": "private",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    conn = vpc_lab.db()
    subnets = conn.execute(
        "SELECT COUNT(*) FROM vpc_subnets WHERE vpc_id = ?",
        (vpc["id"],),
    ).fetchone()[0]
    conn.close()
    assert subnets == 1


def test_security_group_rule_allows_and_denies_traffic(client):
    import security_group_lab

    response = client.post(
        "/practice/security-groups/create",
        data={"name": "Test Web SG", "description": "Regression test"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    conn = security_group_lab.db()
    group = conn.execute(
        "SELECT id FROM security_groups WHERE name = ?",
        ("Test Web SG",),
    ).fetchone()
    conn.close()
    assert group is not None

    response = client.post(
        f"/practice/security-groups/{group['id']}/rule/create",
        data={
            "protocol": "tcp",
            "source_cidr": "203.0.113.0/24",
            "from_port": "80",
            "to_port": "80",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    conn = security_group_lab.db()
    rules = conn.execute(
        "SELECT COUNT(*) FROM security_group_rules WHERE group_id = ?",
        (group["id"],),
    ).fetchone()[0]
    conn.close()
    assert rules == 1

    allowed = client.post(
        "/practice/security-groups/simulate",
        data={
            "source_ip": "203.0.113.10",
            "group_id": str(group["id"]),
            "protocol": "tcp",
            "port": "80",
        },
        follow_redirects=True,
    )
    assert allowed.status_code == 200
    assert b"ALLOWED" in allowed.data

    denied = client.post(
        "/practice/security-groups/simulate",
        data={
            "source_ip": "198.51.100.10",
            "group_id": str(group["id"]),
            "protocol": "tcp",
            "port": "80",
        },
        follow_redirects=True,
    )
    assert denied.status_code == 200
    assert b"DENIED" in denied.data


def test_route53_creates_a_record_and_finds_it(client):
    import route53_lab

    response = client.post(
        "/practice/route53/zone/create",
        data={"domain": "example.com"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    conn = route53_lab.db()
    zone = conn.execute(
        "SELECT id FROM hosted_zones WHERE domain = ?",
        ("example.com",),
    ).fetchone()
    conn.close()
    assert zone is not None

    response = client.post(
        "/practice/route53/record/create",
        data={
            "zone_id": str(zone["id"]),
            "record_name": "www.example.com",
            "record_type": "A",
            "record_value": "192.0.2.10",
            "ttl": "300",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    lookup = client.get(
        "/practice/route53/lookup?domain=www.example.com"
    )
    assert lookup.status_code == 200
    assert b"192.0.2.10" in lookup.data


def test_route53_rejects_invalid_a_record_ip(client):
    import route53_lab

    client.post(
        "/practice/route53/zone/create",
        data={"domain": "example.com"},
        follow_redirects=True,
    )

    conn = route53_lab.db()
    zone = conn.execute(
        "SELECT id FROM hosted_zones WHERE domain = ?",
        ("example.com",),
    ).fetchone()
    conn.close()
    assert zone is not None

    response = client.post(
        "/practice/route53/record/create",
        data={
            "zone_id": str(zone["id"]),
            "record_name": "www.example.com",
            "record_type": "A",
            "record_value": "not-an-ip",
            "ttl": "300",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    conn = route53_lab.db()
    count = conn.execute(
        "SELECT COUNT(*) FROM dns_records WHERE zone_id = ?",
        (zone["id"],),
    ).fetchone()[0]
    conn.close()
    assert count == 0


def test_route53_rejects_duplicate_hosted_zone(client):
    client.post(
        "/practice/route53/zone/create",
        data={"domain": "example.com"},
        follow_redirects=True,
    )

    response = client.post(
        "/practice/route53/zone/create",
        data={"domain": "EXAMPLE.COM"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    import route53_lab

    conn = route53_lab.db()
    count = conn.execute(
        "SELECT COUNT(*) FROM hosted_zones WHERE lower(domain) = ?",
        ("example.com",),
    ).fetchone()[0]
    conn.close()
    assert count == 1


def test_nat_gateway_and_private_subnet_connectivity(client):
    import vpc_lab

    # Create a VPC and public/private subnets.
    client.post(
        "/practice/vpc/create",
        data={"name": "NAT Test VPC", "cidr": "10.20.0.0/16"},
        follow_redirects=True,
    )

    conn = vpc_lab.db()
    vpc = conn.execute(
        "SELECT id FROM vpcs WHERE name = ?", ("NAT Test VPC",)
    ).fetchone()
    conn.close()
    assert vpc is not None

    vpc_id = vpc["id"]

    client.post(
        f"/practice/vpc/{vpc_id}/internet-gateway",
        data={"action": "attach"},
        follow_redirects=True,
    )

    client.post(
        "/practice/vpc/subnet/create",
        data={
            "vpc_id": str(vpc_id),
            "name": "NAT Public",
            "cidr": "10.20.1.0/24",
            "subnet_type": "public",
        },
        follow_redirects=True,
    )
    client.post(
        "/practice/vpc/subnet/create",
        data={
            "vpc_id": str(vpc_id),
            "name": "NAT Private",
            "cidr": "10.20.2.0/24",
            "subnet_type": "private",
        },
        follow_redirects=True,
    )

    conn = vpc_lab.db()
    public_subnet = conn.execute(
        "SELECT id FROM vpc_subnets WHERE vpc_id = ? AND name = ?",
        (vpc_id, "NAT Public"),
    ).fetchone()
    private_subnet = conn.execute(
        "SELECT id FROM vpc_subnets WHERE vpc_id = ? AND name = ?",
        (vpc_id, "NAT Private"),
    ).fetchone()
    conn.close()
    assert public_subnet is not None
    assert private_subnet is not None

    # A public subnet without NAT should not pass as a private subnet.
    blocked = client.post(
        "/practice/vpc/connectivity-test",
        data={
            "subnet_id": str(private_subnet["id"]),
            "destination": "8.8.8.8",
        },
        follow_redirects=True,
    )
    assert blocked.status_code == 200
    assert b"SIMULATED BLOCK" in blocked.data

    # NAT creation should work after IGW attachment and public routing.
    created = client.post(
        "/practice/vpc/nat/create",
        data={
            "public_subnet_id": str(public_subnet["id"]),
            "name": "Test NAT",
        },
        follow_redirects=True,
    )
    assert created.status_code == 200

    conn = vpc_lab.db()
    nat = conn.execute(
        "SELECT id FROM vpc_nat_gateways WHERE vpc_id = ?", (vpc_id,)
    ).fetchone()
    conn.close()
    assert nat is not None

    # Configure the private subnet's default route through NAT.
    routed = client.post(
        "/practice/vpc/nat/route",
        data={"subnet_id": str(private_subnet["id"])},
        follow_redirects=True,
    )
    assert routed.status_code == 200

    conn = vpc_lab.db()
    route = conn.execute(
        "SELECT target FROM vpc_routes WHERE subnet_id = ? "
        "AND destination = '0.0.0.0/0'",
        (private_subnet["id"],),
    ).fetchone()
    conn.close()
    assert route is not None
    assert route["target"] == "nat"

    allowed = client.post(
        "/practice/vpc/connectivity-test",
        data={
            "subnet_id": str(private_subnet["id"]),
            "destination": "8.8.8.8",
        },
        follow_redirects=True,
    )
    assert allowed.status_code == 200
    assert b"SIMULATED PASS" in allowed.data
    assert b"NAT Gateway ke through" in allowed.data


def test_nat_gateway_rejects_private_subnet(client):
    import vpc_lab

    client.post(
        "/practice/vpc/create",
        data={"name": "Invalid NAT VPC", "cidr": "10.30.0.0/16"},
        follow_redirects=True,
    )

    conn = vpc_lab.db()
    vpc = conn.execute(
        "SELECT id FROM vpcs WHERE name = ?", ("Invalid NAT VPC",)
    ).fetchone()
    conn.close()
    assert vpc is not None

    vpc_id = vpc["id"]
    client.post(
        "/practice/vpc/subnet/create",
        data={
            "vpc_id": str(vpc_id),
            "name": "Private Only",
            "cidr": "10.30.1.0/24",
            "subnet_type": "private",
        },
        follow_redirects=True,
    )

    conn = vpc_lab.db()
    private_subnet = conn.execute(
        "SELECT id FROM vpc_subnets WHERE vpc_id = ?",
        (vpc_id,),
    ).fetchone()
    conn.close()
    assert private_subnet is not None

    response = client.post(
        "/practice/vpc/nat/create",
        data={
            "public_subnet_id": str(private_subnet["id"]),
            "name": "Invalid NAT",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    conn = vpc_lab.db()
    count = conn.execute(
        "SELECT COUNT(*) FROM vpc_nat_gateways WHERE vpc_id = ?",
        (vpc_id,),
    ).fetchone()[0]
    conn.close()
    assert count == 0


def test_igw_attach_detach_and_public_subnet_routing(client):
    import vpc_lab

    # Create a VPC and public subnet.
    client.post(
        "/practice/vpc/create",
        data={"name": "IGW Regression VPC", "cidr": "10.40.0.0/16"},
        follow_redirects=True,
    )

    conn = vpc_lab.db()
    vpc = conn.execute(
        "SELECT id FROM vpcs WHERE name = ?",
        ("IGW Regression VPC",),
    ).fetchone()
    conn.close()
    assert vpc is not None

    vpc_id = vpc["id"]

    client.post(
        "/practice/vpc/subnet/create",
        data={
            "vpc_id": str(vpc_id),
            "name": "IGW Public Subnet",
            "cidr": "10.40.1.0/24",
            "subnet_type": "public",
        },
        follow_redirects=True,
    )

    conn = vpc_lab.db()
    subnet = conn.execute(
        "SELECT id FROM vpc_subnets WHERE vpc_id = ? AND name = ?",
        (vpc_id, "IGW Public Subnet"),
    ).fetchone()
    conn.close()
    assert subnet is not None

    subnet_id = subnet["id"]

    # Attach IGW and verify the default route.
    attached = client.post(
        f"/practice/vpc/{vpc_id}/internet-gateway",
        data={"action": "attach"},
        follow_redirects=True,
    )
    assert attached.status_code == 200

    conn = vpc_lab.db()
    route = conn.execute(
        "SELECT target FROM vpc_routes "
        "WHERE subnet_id = ? AND destination = '0.0.0.0/0'",
        (subnet_id,),
    ).fetchone()
    conn.close()
    assert route is not None
    assert route["target"] == "igw"

    # Public connectivity should pass while IGW is attached.
    allowed = client.post(
        "/practice/vpc/connectivity-test",
        data={"subnet_id": str(subnet_id), "destination": "8.8.8.8"},
        follow_redirects=True,
    )
    assert allowed.status_code == 200
    assert b"SIMULATED PASS" in allowed.data
    assert b"IGW ke through" in allowed.data

    # Detach IGW and confirm its default route is removed.
    detached = client.post(
        f"/practice/vpc/{vpc_id}/internet-gateway",
        data={"action": "detach"},
        follow_redirects=True,
    )
    assert detached.status_code == 200

    conn = vpc_lab.db()
    route = conn.execute(
        "SELECT target FROM vpc_routes "
        "WHERE subnet_id = ? AND destination = '0.0.0.0/0'",
        (subnet_id,),
    ).fetchone()
    conn.close()
    assert route is None

    # Connectivity should now be blocked.
    blocked = client.post(
        "/practice/vpc/connectivity-test",
        data={"subnet_id": str(subnet_id), "destination": "8.8.8.8"},
        follow_redirects=True,
    )
    assert blocked.status_code == 200
    assert b"SIMULATED BLOCK" in blocked.data


def test_nat_route_rejects_public_subnet(client):
    import vpc_lab

    client.post(
        "/practice/vpc/create",
        data={"name": "NAT Route Reject VPC", "cidr": "10.50.0.0/16"},
        follow_redirects=True,
    )

    conn = vpc_lab.db()
    vpc = conn.execute(
        "SELECT id FROM vpcs WHERE name = ?",
        ("NAT Route Reject VPC",),
    ).fetchone()
    conn.close()
    assert vpc is not None

    vpc_id = vpc["id"]

    client.post(
        "/practice/vpc/subnet/create",
        data={
            "vpc_id": str(vpc_id),
            "name": "Public Subnet",
            "cidr": "10.50.1.0/24",
            "subnet_type": "public",
        },
        follow_redirects=True,
    )

    conn = vpc_lab.db()
    subnet = conn.execute(
        "SELECT id FROM vpc_subnets WHERE vpc_id = ? AND name = ?",
        (vpc_id, "Public Subnet"),
    ).fetchone()
    conn.close()
    assert subnet is not None

    response = client.post(
        "/practice/vpc/nat/route",
        data={"subnet_id": str(subnet["id"])},
        follow_redirects=True,
    )
    assert response.status_code == 200

    conn = vpc_lab.db()
    route = conn.execute(
        "SELECT target FROM vpc_routes "
        "WHERE subnet_id = ? AND destination = '0.0.0.0/0'",
        (subnet["id"],),
    ).fetchone()
    conn.close()

    assert route is None or route["target"] != "nat"


def test_connectivity_rejects_invalid_destination_ip(client):
    import vpc_lab

    client.post(
        "/practice/vpc/create",
        data={"name": "Invalid IP Test VPC", "cidr": "10.60.0.0/16"},
        follow_redirects=True,
    )

    conn = vpc_lab.db()
    vpc = conn.execute(
        "SELECT id FROM vpcs WHERE name = ?",
        ("Invalid IP Test VPC",),
    ).fetchone()
    conn.close()
    assert vpc is not None

    client.post(
        "/practice/vpc/subnet/create",
        data={
            "vpc_id": str(vpc["id"]),
            "name": "IP Test Subnet",
            "cidr": "10.60.1.0/24",
            "subnet_type": "public",
        },
        follow_redirects=True,
    )

    conn = vpc_lab.db()
    subnet = conn.execute(
        "SELECT id FROM vpc_subnets WHERE vpc_id = ? AND name = ?",
        (vpc["id"], "IP Test Subnet"),
    ).fetchone()
    conn.close()
    assert subnet is not None

    response = client.post(
        "/practice/vpc/connectivity-test",
        data={
            "subnet_id": str(subnet["id"]),
            "destination": "not-an-ip",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"SIMULATED PASS" not in response.data


def _iam_create_user_for_test(client, name):
    import iam_lab

    client.post("/practice/iam/user/create", data={"name": name})
    conn = iam_lab.db()
    row = conn.execute(
        "SELECT id FROM iam_users WHERE name = ?", (name,)
    ).fetchone()
    conn.close()
    assert row is not None
    return row["id"]


def _iam_create_policy_for_test(client, name, effect, action, resource):
    import iam_lab

    client.post(
        "/practice/iam/policy/create",
        data={
            "name": name,
            "effect": effect,
            "action": action,
            "resource": resource,
        },
    )
    conn = iam_lab.db()
    row = conn.execute(
        "SELECT id FROM iam_policies WHERE name = ?", (name,)
    ).fetchone()
    conn.close()
    assert row is not None
    return row["id"]


def _iam_attach_policy_for_test(client, policy_id, principal_type, principal_id):
    return client.post(
        "/practice/iam/policy/attach",
        data={
            "policy_id": str(policy_id),
            "principal_type": principal_type,
            "principal_id": str(principal_id),
        },
        follow_redirects=True,
    )


def _iam_simulate_for_test(client, user_id, action="s3:GetObject",
                           resource="reports/file.pdf"):
    return client.post(
        "/practice/iam/simulate",
        data={
            "principal_type": "user",
            "principal_id": str(user_id),
            "action": action,
            "resource": resource,
        },
        follow_redirects=True,
    )


def test_iam_defaults_to_deny_without_matching_allow(client):
    user_id = _iam_create_user_for_test(client, "default-deny-user")

    response = _iam_simulate_for_test(client, user_id)

    assert response.status_code == 200
    assert b"Decision: DENY" in response.data
    assert b"No matching Allow policy was found" in response.data


def test_iam_matching_allow_policy_grants_access(client):
    user_id = _iam_create_user_for_test(client, "allow-user")
    policy_id = _iam_create_policy_for_test(
        client, "allow-s3-read", "Allow", "s3:GetObject", "reports/*"
    )
    _iam_attach_policy_for_test(client, policy_id, "user", user_id)

    response = _iam_simulate_for_test(client, user_id)

    assert response.status_code == 200
    assert b"Decision: ALLOW" in response.data
    assert b"allow-s3-read" in response.data


def test_iam_explicit_deny_overrides_allow(client):
    user_id = _iam_create_user_for_test(client, "deny-overrides-user")

    allow_id = _iam_create_policy_for_test(
        client, "allow-reports", "Allow", "s3:GetObject", "reports/*"
    )
    deny_id = _iam_create_policy_for_test(
        client, "deny-sensitive", "Deny", "s3:GetObject",
        "reports/secret.pdf"
    )
    _iam_attach_policy_for_test(client, allow_id, "user", user_id)
    _iam_attach_policy_for_test(client, deny_id, "user", user_id)

    response = _iam_simulate_for_test(
        client, user_id, resource="reports/secret.pdf"
    )

    assert response.status_code == 200
    assert b"Decision: DENY" in response.data
    assert b"explicit Deny policy takes precedence" in response.data


def test_iam_user_inherits_attached_group_policy(client):
    import iam_lab

    user_id = _iam_create_user_for_test(client, "group-policy-user")
    client.post(
        "/practice/iam/group/create",
        data={"name": "s3-readers"},
        follow_redirects=True,
    )

    conn = iam_lab.db()
    group = conn.execute(
        "SELECT id FROM iam_groups WHERE name = ?", ("s3-readers",)
    ).fetchone()
    conn.close()
    assert group is not None

    client.post(
        "/practice/iam/membership",
        data={"user_id": str(user_id), "group_id": str(group["id"])},
        follow_redirects=True,
    )

    policy_id = _iam_create_policy_for_test(
        client, "group-s3-read", "Allow", "s3:GetObject", "reports/*"
    )
    _iam_attach_policy_for_test(
        client, policy_id, "group", group["id"]
    )

    response = _iam_simulate_for_test(client, user_id)

    assert response.status_code == 200
    assert b"Decision: ALLOW" in response.data
    assert b"group-s3-read" in response.data


# Additional IAM validation and lifecycle tests.
def test_iam_rejects_blank_user_name(client):
    response = client.post(
        "/practice/iam/user/create",
        data={"name": "   "},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"User name is required." in response.data


def test_iam_rejects_duplicate_user_name(client):
    import iam_lab

    _iam_create_user_for_test(client, "duplicate-user")
    response = client.post(
        "/practice/iam/user/create",
        data={"name": "duplicate-user"},
        follow_redirects=True,
    )

    assert b"That user name already exists." in response.data
    conn = iam_lab.db()
    count = conn.execute(
        "SELECT COUNT(*) FROM iam_users WHERE name = ?",
        ("duplicate-user",),
    ).fetchone()[0]
    conn.close()
    assert count == 1


@pytest.mark.parametrize(
    "data",
    [
        {"name": "", "effect": "Allow", "action": "s3:GetObject",
         "resource": "reports/*"},
        {"name": "missing-action", "effect": "Allow",
         "action": "", "resource": "reports/*"},
        {"name": "missing-resource", "effect": "Allow",
         "action": "s3:GetObject", "resource": ""},
        {"name": "bad-effect", "effect": "Permit",
         "action": "s3:GetObject", "resource": "reports/*"},
    ],
)
def test_iam_rejects_invalid_policy_input(client, data):
    response = client.post(
        "/practice/iam/policy/create",
        data=data,
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Enter a policy name, valid effect, action and resource." in response.data


def test_iam_rejects_invalid_policy_principal_type(client):
    user_id = _iam_create_user_for_test(client, "invalid-principal-user")
    policy_id = _iam_create_policy_for_test(
        client, "invalid-principal-policy", "Allow",
        "s3:GetObject", "reports/*",
    )

    response = client.post(
        "/practice/iam/policy/attach",
        data={
            "policy_id": str(policy_id),
            "principal_type": "service",
            "principal_id": str(user_id),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Invalid identity type." in response.data


def test_iam_rejects_attachment_to_missing_identity(client):
    policy_id = _iam_create_policy_for_test(
        client, "missing-identity-policy", "Allow",
        "s3:GetObject", "reports/*",
    )

    response = client.post(
        "/practice/iam/policy/attach",
        data={
            "policy_id": str(policy_id),
            "principal_type": "user",
            "principal_id": "999999",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Selected policy or identity does not exist." in response.data


def test_iam_rejects_duplicate_policy_attachment(client):
    import iam_lab

    user_id = _iam_create_user_for_test(client, "duplicate-attachment-user")
    policy_id = _iam_create_policy_for_test(
        client, "duplicate-attachment-policy", "Allow",
        "s3:GetObject", "reports/*",
    )

    _iam_attach_policy_for_test(client, policy_id, "user", user_id)
    response = _iam_attach_policy_for_test(
        client, policy_id, "user", user_id
    )

    assert b"That policy is already attached." in response.data
    conn = iam_lab.db()
    count = conn.execute(
        """SELECT COUNT(*) FROM iam_policy_attachments
           WHERE policy_id = ? AND principal_type = 'user'
           AND principal_id = ?""",
        (policy_id, user_id),
    ).fetchone()[0]
    conn.close()
    assert count == 1


def test_iam_deleting_policy_removes_its_attachments(client):
    import iam_lab

    user_id = _iam_create_user_for_test(client, "policy-delete-user")
    policy_id = _iam_create_policy_for_test(
        client, "policy-to-delete", "Allow",
        "s3:GetObject", "reports/*",
    )
    _iam_attach_policy_for_test(client, policy_id, "user", user_id)

    response = client.post(
        f"/practice/iam/policy/{policy_id}/delete",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Policy and its attachments deleted." in response.data

    conn = iam_lab.db()
    policy_count = conn.execute(
        "SELECT COUNT(*) FROM iam_policies WHERE id = ?",
        (policy_id,),
    ).fetchone()[0]
    attachment_count = conn.execute(
        "SELECT COUNT(*) FROM iam_policy_attachments WHERE policy_id = ?",
        (policy_id,),
    ).fetchone()[0]
    conn.close()

    assert policy_count == 0
    assert attachment_count == 0


def test_iam_deleting_user_removes_user_policy_attachments(client):
    import iam_lab

    user_id = _iam_create_user_for_test(client, "user-delete-test")
    policy_id = _iam_create_policy_for_test(
        client, "user-delete-policy", "Allow",
        "s3:GetObject", "reports/*",
    )
    _iam_attach_policy_for_test(client, policy_id, "user", user_id)

    response = client.post(
        f"/practice/iam/user/{user_id}/delete",
        follow_redirects=True,
    )
    assert response.status_code == 200

    conn = iam_lab.db()
    user_count = conn.execute(
        "SELECT COUNT(*) FROM iam_users WHERE id = ?", (user_id,)
    ).fetchone()[0]
    attachment_count = conn.execute(
        """SELECT COUNT(*) FROM iam_policy_attachments
           WHERE principal_type = 'user' AND principal_id = ?""",
        (user_id,),
    ).fetchone()[0]
    conn.close()

    assert user_count == 0
    assert attachment_count == 0


def test_iam_action_wildcard_allows_matching_action(client):
    user_id = _iam_create_user_for_test(client, "wildcard-action-user")
    policy_id = _iam_create_policy_for_test(
        client, "wildcard-read-policy", "Allow", "s3:Get*", "reports/*"
    )
    _iam_attach_policy_for_test(client, policy_id, "user", user_id)

    response = _iam_simulate_for_test(
        client, user_id, action="s3:GetObject"
    )

    assert response.status_code == 200
    assert b"Decision: ALLOW" in response.data


def test_iam_action_wildcard_does_not_allow_unmatched_action(client):
    user_id = _iam_create_user_for_test(client, "wildcard-put-user")
    policy_id = _iam_create_policy_for_test(
        client, "wildcard-read-only", "Allow", "s3:Get*", "reports/*"
    )
    _iam_attach_policy_for_test(client, policy_id, "user", user_id)

    response = _iam_simulate_for_test(
        client, user_id, action="s3:PutObject"
    )

    assert response.status_code == 200
    assert b"Decision: DENY" in response.data


def test_iam_narrow_action_policy_does_not_match_broad_request(client):
    user_id = _iam_create_user_for_test(client, "broad-action-user")
    policy_id = _iam_create_policy_for_test(
        client, "narrow-read-policy", "Allow",
        "s3:GetObject", "reports/*"
    )
    _iam_attach_policy_for_test(client, policy_id, "user", user_id)

    response = _iam_simulate_for_test(
        client, user_id, action="s3:*"
    )

    assert response.status_code == 200
    assert b"Decision: DENY" in response.data

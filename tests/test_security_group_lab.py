import sqlite3

import pytest


@pytest.fixture
def security_client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "security_test.db")
    original_connect = sqlite3.connect

    def isolated_connect(database, *args, **kwargs):
        return original_connect(db_path, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", isolated_connect)

    import app as cloudsim_app
    import vpc_lab
    import security_group_lab
    import route53_lab
    import iam_lab
    import extra_services_lab

    monkeypatch.setattr(cloudsim_app, "DB", db_path)
    monkeypatch.setattr(vpc_lab, "DB", db_path)
    monkeypatch.setattr(security_group_lab, "DB", db_path)
    monkeypatch.setattr(route53_lab, "DB", db_path)
    monkeypatch.setattr(iam_lab, "DB", db_path)
    monkeypatch.setattr(extra_services_lab, "DB", db_path)

    cloudsim_app.init_db()
    vpc_lab.init_vpc_db()
    vpc_lab.init_nat_db()
    security_group_lab.init_security_group_db()
    route53_lab.init_route53_db()
    iam_lab.init_iam_db()
    extra_services_lab.init_extra_services_db()

    cloudsim_app.app.config.update(TESTING=True)

    with cloudsim_app.app.test_client() as client:
        yield client


def create_group(client, name="pytest-web-sg"):
    response = client.post(
        "/practice/security-groups/create",
        data={"name": name, "description": "Automated test group"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    from security_group_lab import db

    conn = db()
    group = conn.execute(
        "SELECT * FROM security_groups WHERE name = ?", (name,)
    ).fetchone()
    conn.close()
    assert group is not None
    return group["id"]


def add_tcp_rule(client, group_id, source="203.0.113.10/32",
                 from_port="80", to_port="80"):
    return client.post(
        f"/practice/security-groups/{group_id}/rule/create",
        data={
            "protocol": "tcp",
            "from_port": from_port,
            "to_port": to_port,
            "source_cidr": source,
        },
        follow_redirects=True,
    )


def test_security_group_page_loads(security_client):
    response = security_client.get(
        "/practice/security-groups/", follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Security Group Lab" in response.data


def test_create_security_group(security_client):
    group_id = create_group(security_client)
    assert group_id > 0


def test_valid_inbound_rule_is_saved(security_client):
    group_id = create_group(security_client)
    response = add_tcp_rule(security_client, group_id)

    assert response.status_code == 200
    assert b"Inbound allow rule added" in response.data

    from security_group_lab import db

    conn = db()
    rule = conn.execute(
        "SELECT * FROM security_group_rules WHERE group_id = ?",
        (group_id,),
    ).fetchone()
    conn.close()

    assert rule is not None
    assert rule["protocol"] == "tcp"
    assert rule["from_port"] == 80
    assert rule["to_port"] == 80
    assert rule["source_cidr"] == "203.0.113.10/32"


@pytest.mark.parametrize(
    "source",
    ["not-a-cidr", "203.0.113.10/99", ""],
)
def test_invalid_cidr_is_rejected(security_client, source):
    group_id = create_group(security_client)
    response = add_tcp_rule(security_client, group_id, source=source)

    assert response.status_code == 200
    assert b"Invalid source CIDR" in response.data

    from security_group_lab import db

    conn = db()
    count = conn.execute(
        "SELECT COUNT(*) FROM security_group_rules WHERE group_id = ?",
        (group_id,),
    ).fetchone()[0]
    conn.close()
    assert count == 0


@pytest.mark.parametrize(
    "from_port,to_port",
    [("0", "80"), ("81", "80"), ("1", "65536")],
)
def test_invalid_port_range_is_rejected(
    security_client, from_port, to_port
):
    group_id = create_group(security_client)
    response = add_tcp_rule(
        security_client,
        group_id,
        from_port=from_port,
        to_port=to_port,
    )

    assert response.status_code == 200
    assert b"Ports must be between" in response.data

    from security_group_lab import db

    conn = db()
    count = conn.execute(
        "SELECT COUNT(*) FROM security_group_rules WHERE group_id = ?",
        (group_id,),
    ).fetchone()[0]
    conn.close()
    assert count == 0


def test_matching_traffic_is_allowed(security_client):
    group_id = create_group(security_client)
    add_tcp_rule(security_client, group_id)

    response = security_client.post(
        "/practice/security-groups/simulate",
        data={
            "group_id": str(group_id),
            "source_ip": "203.0.113.10",
            "protocol": "tcp",
            "port": "80",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Simulated traffic ALLOWED" in response.data


def test_non_matching_source_is_denied(security_client):
    group_id = create_group(security_client)
    add_tcp_rule(security_client, group_id)

    response = security_client.post(
        "/practice/security-groups/simulate",
        data={
            "group_id": str(group_id),
            "source_ip": "198.51.100.20",
            "protocol": "tcp",
            "port": "80",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Simulated traffic DENIED" in response.data


def test_group_deletion_removes_its_rules(security_client):
    group_id = create_group(security_client)
    add_tcp_rule(security_client, group_id)

    from security_group_lab import db

    conn = db()
    before = conn.execute(
        "SELECT COUNT(*) FROM security_group_rules WHERE group_id = ?",
        (group_id,),
    ).fetchone()[0]
    conn.close()
    assert before == 1

    response = security_client.post(
        f"/practice/security-groups/{group_id}/delete",
        follow_redirects=True,
    )
    assert response.status_code == 200

    conn = db()
    group_count = conn.execute(
        "SELECT COUNT(*) FROM security_groups WHERE id = ?", (group_id,)
    ).fetchone()[0]
    rule_count = conn.execute(
        "SELECT COUNT(*) FROM security_group_rules WHERE group_id = ?",
        (group_id,),
    ).fetchone()[0]
    conn.close()

    assert group_count == 0
    assert rule_count == 0

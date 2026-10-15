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

    # Sabhi modules ko ek hi temporary database par set karo.
    monkeypatch.setattr(cloudsim_app, "DB", db_path)
    monkeypatch.setattr(vpc_lab, "DB", db_path)
    monkeypatch.setattr(security_group_lab, "DB", db_path)
    monkeypatch.setattr(route53_lab, "DB", db_path)

    # Temporary database mein tables initialize karo.
    cloudsim_app.init_db()
    vpc_lab.init_vpc_db()
    vpc_lab.init_nat_db()
    security_group_lab.init_security_group_db()
    route53_lab.init_route53_db()

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

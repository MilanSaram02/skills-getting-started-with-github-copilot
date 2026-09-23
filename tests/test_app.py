from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

from fastapi.testclient import TestClient

from src.app import app


def test_root_redirects_to_static_index(client):
    # Arrange
    expected_location = "/static/index.html"

    # Act
    response = client.get("/", follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == expected_location


def test_get_activities_returns_seeded_activity_data(client):
    # Arrange
    activity_name = "Chess Club"

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    activity = response.json()[activity_name]
    assert activity["description"] == "Learn strategies and compete in chess tournaments"
    assert activity["participants"] == [
        "michael@mergington.edu",
        "daniel@mergington.edu",
    ]


def test_signup_adds_participant(client):
    # Arrange
    activity_name = "Art Club"
    email = "student@mergington.edu"

    # Act
    response = client.post(
        f"/activities/{quote(activity_name)}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "message": f"Signed up {email} for {activity_name}"
    }
    activity = client.get("/activities").json()[activity_name]
    assert email in activity["participants"]


def test_duplicate_signup_is_rejected(client):
    # Arrange
    activity_name = "Chess Club"
    email = "michael@mergington.edu"

    # Act
    response = client.post(
        f"/activities/{quote(activity_name)}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Student already signed up for this activity"
    }
    activity = client.get("/activities").json()[activity_name]
    assert activity["participants"].count(email) == 1


def test_concurrent_duplicate_signup_is_rejected(client):
    # Arrange
    activity_name = "Art Club"
    email = "student@mergington.edu"

    def signup():
        with TestClient(app) as concurrent_client:
            return concurrent_client.post(
                f"/activities/{quote(activity_name)}/signup",
                params={"email": email},
            )

    # Act
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: signup(), range(2)))

    # Assert
    assert sorted(response.status_code for response in responses) == [200, 400]
    activity = client.get("/activities").json()[activity_name]
    assert activity["participants"].count(email) == 1


def test_signup_for_unknown_activity_is_rejected(client):
    # Arrange
    activity_name = "Unknown Club"
    email = "student@mergington.edu"

    # Act
    response = client.post(
        f"/activities/{quote(activity_name)}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_unregister_removes_participant(client):
    # Arrange
    activity_name = "Chess Club"
    email = "michael@mergington.edu"

    # Act
    response = client.delete(
        f"/activities/{quote(activity_name)}/signup/{quote(email)}"
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "message": f"Unregistered {email} from {activity_name}"
    }
    activity = client.get("/activities").json()[activity_name]
    assert email not in activity["participants"]


def test_unregister_from_unknown_activity_is_rejected(client):
    # Arrange
    activity_name = "Unknown Club"
    email = "student@mergington.edu"

    # Act
    response = client.delete(
        f"/activities/{quote(activity_name)}/signup/{quote(email)}"
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_unregistering_unknown_participant_is_rejected(client):
    # Arrange
    activity_name = "Chess Club"
    email = "not-registered@mergington.edu"

    # Act
    response = client.delete(
        f"/activities/{quote(activity_name)}/signup/{quote(email)}"
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {
        "detail": "Student is not signed up for this activity"
    }

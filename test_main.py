"""quick tests so I don't break auth/tasks"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db
from main import app

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override the get_db dependency to use test database"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()
    # TODO: swap this to a fixture later maybe


# Override the database dependency
app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Create fresh database tables before each test"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_signup_success():
    """Test successful user signup"""
    response = client.post(
        "/auth/signup",
        json={"username": "testuser", "password": "testpass123"}
    )
    assert response.status_code == 201  # kinda basic but fine
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_signup_duplicate_username():
    """Test signup fails with duplicate username"""
    # Create first user
    client.post(
        "/auth/signup",
        json={"username": "testuser", "password": "testpass123"}
    )

    # Try to create second user with same username
    response = client.post(
        "/auth/signup",
        json={"username": "testuser", "password": "differentpass"}
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


def test_login_success():
    """Test successful login"""
    # Create user
    client.post(
        "/auth/signup",
        json={"username": "testuser", "password": "testpass123"}
    )

    # Login
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpass123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password():
    """Test login fails with wrong password"""
    # Create user
    client.post(
        "/auth/signup",
        json={"username": "testuser", "password": "testpass123"}
    )

    # Try login with wrong password
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "wrong" in response.json()["detail"].lower()


def test_create_and_get_tasks():
    """Test creating and retrieving tasks with authentication"""
    # Signup and get token
    signup_response = client.post(
        "/auth/signup",
        json={"username": "testuser", "password": "testpass123"}
    )
    token = signup_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a task
    create_response = client.post(
        "/tasks",
        json={"title": "Test Task", "description": "Test Description"},
        headers=headers
    )
    assert create_response.status_code == 201
    task_data = create_response.json()
    assert task_data["title"] == "Test Task"
    assert task_data["description"] == "Test Description"
    assert task_data["completed"] is False

    # Get all tasks
    get_response = client.get("/tasks", headers=headers)
    assert get_response.status_code == 200
    tasks = get_response.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Test Task"


def test_unauthorized_access():
    """Test that accessing tasks without token returns 401"""
    response = client.get("/tasks")
    assert response.status_code == 401


def test_cannot_access_other_users_tasks():
    """Test that users cannot access or modify other users' tasks"""
    # Create first user and their task
    user1_response = client.post(
        "/auth/signup",
        json={"username": "user1", "password": "pass1"}
    )
    user1_token = user1_response.json()["access_token"]
    user1_headers = {"Authorization": f"Bearer {user1_token}"}

    task_response = client.post(
        "/tasks",
        json={"title": "User1's Task", "description": "Private task"},
        headers=user1_headers
    )
    task_id = task_response.json()["id"]

    # Create second user
    user2_response = client.post(
        "/auth/signup",
        json={"username": "user2", "password": "pass2"}
    )
    user2_token = user2_response.json()["access_token"]
    user2_headers = {"Authorization": f"Bearer {user2_token}"}

    # User2 tries to update User1's task - should fail with 403
    update_response = client.patch(
        f"/tasks/{task_id}",
        json={"title": "Hacked!"},
        headers=user2_headers
    )
    assert update_response.status_code == 403
    assert "not your task" in update_response.json()["detail"].lower()

    # User2 tries to delete User1's task - should fail with 403
    delete_response = client.delete(
        f"/tasks/{task_id}",
        headers=user2_headers
    )
    assert delete_response.status_code == 403
    assert "not your task" in delete_response.json()["detail"].lower()

    # User2 should only see their own tasks (empty list)
    get_response = client.get("/tasks", headers=user2_headers)
    assert get_response.status_code == 200
    assert len(get_response.json()) == 0


def test_admin_can_view_all_tasks():
    """Admin role can list all tasks across users"""
    # Create a regular user and a task
    user_response = client.post(
        "/auth/signup",
        json={"username": "regular", "password": "pass"}
    )
    user_token = user_response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}
    client.post(
        "/tasks",
        json={"title": "Regular Task"},
        headers=user_headers
    )

    # Create an admin user
    admin_response = client.post(
        "/auth/signup",
        json={"username": "adminuser", "password": "adminpass", "role": "admin"}
    )
    admin_token = admin_response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Admin should see all tasks (including regular user's task)
    all_tasks_response = client.get("/tasks/all", headers=admin_headers)
    assert all_tasks_response.status_code == 200
    all_tasks = all_tasks_response.json()
    assert any(task["title"] == "Regular Task" for task in all_tasks)


def test_non_admin_cannot_view_all_tasks():
    """Non-admin users should be blocked from admin endpoint"""
    user_response = client.post(
        "/auth/signup",
        json={"username": "plainuser", "password": "pass"}
    )
    token = user_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/tasks/all", headers=headers)
    assert response.status_code == 403
    assert "admin" in response.json()["detail"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

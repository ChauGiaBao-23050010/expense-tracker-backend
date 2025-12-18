#!/usr/bin/env python3
"""
Test script to demonstrate proper authentication flow.
This script shows how to:
1. Register a user
2. Login to get a token
3. Use the token to access protected endpoints
"""

import requests
import json

# Base URL of your FastAPI application
BASE_URL = "http://127.0.0.1:8000"

def test_authentication_flow():
    print("=== Testing Authentication Flow ===")

    # Step 1: Register a new user
    print("\n1. Registering new user...")
    register_data = {
        "username": "testuser",
        "password": "testpassword123",
        "email": "test@example.com",
        "full_name": "Test User"
    }

    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
        if response.status_code == 200:
            print("✓ User registered successfully")
            print(f"Response: {response.json()}")
        else:
            print(f"✗ Registration failed: {response.status_code} - {response.text}")
            # If user already exists, that's okay for testing
            if response.status_code == 400:
                print("User already exists, continuing with login...")
    except Exception as e:
        print(f"✗ Registration error: {str(e)}")
        return

    # Step 2: Login to get token
    print("\n2. Logging in to get token...")
    login_data = {
        "username": "testuser",
        "password": "testpassword123"
    }

    try:
        response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data["access_token"]
            print("✓ Login successful")
            print(f"Access token: {access_token}")
        else:
            print(f"✗ Login failed: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"✗ Login error: {str(e)}")
        return

    # Step 3: Access protected endpoint WITH token
    print("\n3. Accessing protected /users/me endpoint with token...")
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    try:
        response = requests.get(f"{BASE_URL}/users/me", headers=headers)
        if response.status_code == 200:
            print("✓ Successfully accessed protected endpoint")
            print(f"User data: {response.json()}")
        else:
            print(f"✗ Failed to access protected endpoint: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"✗ Protected endpoint access error: {str(e)}")

    # Step 4: Access protected endpoint WITHOUT token (should fail)
    print("\n4. Accessing protected /users/me endpoint WITHOUT token (should fail)...")
    try:
        response = requests.get(f"{BASE_URL}/users/me")
        if response.status_code == 401:
            print("✓ Correctly got 401 Unauthorized (expected behavior)")
            print(f"Response: {response.text}")
        else:
            print(f"✗ Unexpected response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")

if __name__ == "__main__":
    test_authentication_flow()
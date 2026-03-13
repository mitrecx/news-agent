"""Test script for authentication functionality"""

import asyncio
import httpx

BASE_URL = "http://localhost:8000"


async def test_login():
    """Test user login"""
    print("🔐 Testing user login...")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "test", "password": "test"}
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Login successful!")
            print(f"   User: {data['user']['username']}")
            print(f"   Token: {data['access_token'][:50]}...")
            return data['access_token']
        else:
            print(f"❌ Login failed: {response.text}")
            return None


async def test_chat_with_token(token: str):
    """Test chat endpoint with authentication token"""
    print("\n💬 Testing chat with authentication...")

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(
            f"{BASE_URL}/api/chat/stream",
            json={"message": "你好"},
            headers=headers
        )

        if response.status_code == 200:
            print("✅ Chat with authentication successful!")
            print("   Response:")
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    print(f"   {data}")
        else:
            print(f"❌ Chat failed: {response.text}")


async def test_chat_without_auth():
    """Test chat endpoint without authentication (should fail)"""
    print("\n🚫 Testing chat without authentication (should fail)...")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/chat/stream",
            json={"message": "你好"}
        )

        if response.status_code == 401:
            print("✅ Correctly rejected unauthenticated request!")
            print(f"   Status: {response.status_code}")
        else:
            print(f"❌ Should have rejected unauthenticated request!")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("News Agent Authentication Test")
    print("=" * 60)

    # Test login
    token = await test_login()

    if token:
        # Test authenticated chat
        await test_chat_with_token(token)

    # Test that unauthenticated requests are rejected
    await test_chat_without_auth()

    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

"""Test script for Vue.js frontend integration"""

import asyncio
import httpx

BASE_URL = "http://localhost:8000"


async def test_health():
    """Test health endpoint"""
    print("🏥 Testing health endpoint...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        data = response.json()
        print(f"✅ Health check: {data}")
        return data.get("agent_ready", False)


async def test_login():
    """Test login endpoint"""
    print("\n🔐 Testing login endpoint...")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "test", "password": "test"}
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Login successful!")
            print(f"   User: {data['user']['username']}")
            return data["access_token"]
        else:
            print(f"❌ Login failed: {response.text}")
            return None


async def test_chat_stream(token: str):
    """Test chat streaming endpoint"""
    print("\n💬 Testing chat streaming...")
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        async with client.stream(
            "POST",
            f"{BASE_URL}/api/chat/stream",
            json={"message": "你好"},
            headers=headers
        ) as response:
            if response.status_code == 200:
                print("✅ Chat streaming started!")
                print("   Response:")
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            print("\n✅ Chat streaming completed!")
                            break
                        print(f"   {data}")
            else:
                print(f"❌ Chat failed: {response.text}")


async def test_cors():
    """Test CORS headers"""
    print("\n🌐 Testing CORS headers...")
    async with httpx.AsyncClient() as client:
        response = await client.options(
            f"{BASE_URL}/api/auth/login",
            headers={"Origin": "http://localhost:5173"}
        )
        cors_headers = {
            key: response.headers.get(key)
            for key in ["access-control-allow-origin", "access-control-allow-credentials"]
        }
        print(f"   CORS headers: {cors_headers}")
        if "access-control-allow-origin" in response.headers:
            print("✅ CORS is configured!")
        else:
            print("⚠️  CORS might not be properly configured")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Vue.js Frontend Integration Test")
    print("=" * 60)

    # Test health
    agent_ready = await test_health()

    # Test login
    token = await test_login()

    if token and agent_ready:
        # Test chat streaming
        await test_chat_stream(token)

    # Test CORS
    await test_cors()

    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
    print("\n📝 Summary:")
    print("   - Frontend URL: http://localhost:5173")
    print("   - Backend URL:  http://localhost:8000")
    print("   - Test login:   username 'test', password 'test'")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

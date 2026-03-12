"""Main entry point for News Agent"""

import uvicorn
from src.agent.config import get_settings


def main():
    """Start the News Agent server"""
    settings = get_settings()

    print("""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║           🤖 News Agent - 新闻助手                          ║
║                                                            ║
║     Powered by LangChain + DeepSeek                        ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
    """)

    print(f"🚀 Starting server on http://{settings.host}:{settings.port}")
    print(f"📊 Model: {settings.agent_model}")
    print(f"🌐 API Docs: http://{settings.host}:{settings.port}/docs")
    print()

    uvicorn.run(
        "src.api.server:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()

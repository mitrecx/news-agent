"""Run the News Agent server"""

import uvicorn
from src.agent.config import get_settings


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "src.api.server:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )

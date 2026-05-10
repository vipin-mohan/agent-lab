"""
Test client for the PM Career Coach A2A server.

Adapted from a2a-samples/samples/python/agents/helloworld/test_client.py.

Key changes from helloworld:
  - Reads BASE_URL and A2A_BEARER_TOKEN from environment (so we don't hardcode the token)
  - Passes the bearer token as an Authorization header on every httpx request
  - Sends a real PM career coaching prompt instead of "Say hello"
  - Removes the extended-card call (we don't expose one)

Run from pm_career_coach_app/:
    python -m a2a_server.test_client

Required env vars (read from a2a_server/.env via the same loader the server uses):
    A2A_BEARER_TOKEN  (must match the server's token)
    A2A_PUBLIC_URL    (optional, defaults to http://127.0.0.1:8000)
"""

import asyncio
import os

import httpx

from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import display_agent_card, new_text_message
from a2a.types.a2a_pb2 import Role, SendMessageRequest
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH

from .config import settings  # reuses the server's .env loader


# Real coaching prompt — exercises the job_match_score skill end-to-end.
USER_PROMPT = (
    "I have an Adobe Senior Director PM interview coming up. "
    "Score this resume against this JD AND tell me what gaps to close before the interview.\n\n"
    "Resume: 20 years tech, 8 at AWS leading EKS and agentic AI products, "
    "ex-Intel engineer, MBA Berkeley Haas, currently Senior Manager PM at AWS "
    "for the Amazon Quick agent platform.\n\n"
    "JD: Senior Director PM at Adobe, leading Agent Composer for Experience "
    "Platform. Requires 12+ years PM experience, AI/ML platform background, "
    "enterprise SaaS, ability to influence L10 engineering leaders."
)


async def main() -> None:
    base_url = settings.public_url.rstrip("/")
    token = settings.bearer_token

    # Auth header is attached to the httpx client so EVERY request the SDK
    # makes (card resolution, send_message, streaming) carries it.
    auth_headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(headers=auth_headers, timeout=300.0) as httpx_client:
        # --- Discovery ---------------------------------------------------
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
        )

        print(
            f"Fetching agent card from: {base_url}{AGENT_CARD_WELL_KNOWN_PATH}"
        )
        public_card = await resolver.get_agent_card()
        print("\nAgent card:")
        display_agent_card(public_card)

        # --- Non-streaming send -----------------------------------------
        print("\n--- Non-streaming message/send ---")
        config = ClientConfig(streaming=False, httpx_client=httpx_client)
        client = await create_client(agent=public_card, client_config=config)

        message = new_text_message(USER_PROMPT, role=Role.ROLE_USER)
        request = SendMessageRequest(message=message)

        print("Response:")
        async for chunk in client.send_message(request):
            print(chunk)

        # --- Streaming send ---------------------------------------------
        print("\n--- Streaming message/stream ---")
        streaming_config = ClientConfig(streaming=True, httpx_client=httpx_client)
        streaming_client = await create_client(
            agent=public_card, client_config=streaming_config
        )

        streaming_response = streaming_client.send_message(request)
        async for chunk in streaming_response:
            print("Response chunk:")
            print(chunk)



if __name__ == "__main__":
    asyncio.run(main())

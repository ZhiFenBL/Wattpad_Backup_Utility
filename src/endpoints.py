from io import BytesIO
import backoff
from aiohttp import ClientResponseError, ClientSession
from exceptions import PartNotFoundError, StoryNotFoundError
from models import Story
from pydantic import TypeAdapter

story_ta = TypeAdapter(Story)

headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
}


# This function is from https://github.com/TheOnlyWayUp/WattpadDownloader
async def fetch_cookies(username: str, password: str) -> dict:
    # source: https://github.com/TheOnlyWayUp/WP-DM-Export/blob/dd4c7c51cb43f2108e0f63fc10a66cd24a740e4e/src/API/src/main.py#L25-L58
    """Retrieves authorization cookies from Wattpad by logging in with user creds.

    Args:
        username (str): Username.
        password (str): Password.

    Raises:
        ValueError: Bad status code.
        ValueError: No cookies returned.

    Returns:
        dict: Authorization cookies.
    """
    async with ClientSession(headers=headers) as session:
        async with session.post(
            "https://www.wattpad.com/auth/login?nextUrl=%2F&_data=routes%2Fauth.login",
            data={
                "username": username.lower(),
                "password": password,
            },  # the username.lower() is for caching
        ) as response:
            if response.status != 204:
                raise ValueError("Not a 204.")

            cookies = {
                k: v.value
                for k, v in response.cookies.items()  # Thanks https://stackoverflow.com/a/32281245
            }

            if not cookies:
                raise ValueError("No cookies.")

            return cookies

# This function is from https://github.com/TheOnlyWayUp/WattpadDownloader
@backoff.on_exception(backoff.expo, ClientResponseError, max_time=15)
async def fetch_story_content_zip(story_id: int, cookies: dict) -> BytesIO:
    """BytesIO Stream of an Archive of Part Contents for a Story."""
    async with ClientSession(headers=headers, cookies=cookies) as session:
        async with session.get(
            f"https://www.wattpad.com/apiv2/?m=storytext&group_id={story_id}&output=zip"
        ) as response:
            response.raise_for_status()

            bytes_stream = BytesIO(await response.read())

    return bytes_stream


@backoff.on_exception(backoff.expo, ClientResponseError, max_time=15)
async def fetch_library(username: str, cookies: dict) -> list[Story]:
    """List of stories in the users library."""
    async with ClientSession(headers=headers, cookies=cookies) as session:
        nextUrl = f"https://www.wattpad.com/api/v3/users/{username}/library?fields=stories(tags,id,title,createDate,modifyDate,language(name),description,completed,mature,url,isPaywalled,user(username,avatar,description),parts(id,title,deleted),cover,copyright),nextUrl&limit=20"
        stories = []
        while nextUrl:
            async with session.get(nextUrl) as response:
                response.raise_for_status()

                data = await response.json()

                nextUrl = data["nextUrl"] if "nextUrl" in data else None

                for story in data["stories"]:
                    stories.append(story)

        return stories


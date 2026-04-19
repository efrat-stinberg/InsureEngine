import logging
import time

from dotenv import load_dotenv

load_dotenv()

from insure_engine.post_fetcher import fetch_insurance_posts
from insure_engine.comments import handle_post

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 10


def main():
    logger.info("Insure-engine bot started — polling every %ds", POLL_INTERVAL)

    while True:
        try:
            posts = fetch_insurance_posts()
            if posts:
                logger.info("Found %d insurance-related post(s)", len(posts))

            for post in posts:
                try:
                    comment = handle_post(post)
                    logger.info(
                        "Replied to post %s — comment id %s",
                        post["id"],
                        comment["id"],
                    )
                except Exception:
                    logger.exception("Failed to handle post %s", post.get("id"))

        except Exception:
            logger.exception("Error during fetch cycle")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
import logging
import os
from supabase import create_client
from insure_engine.supabase_rag import SupabaseRAGSystem

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
BOT_USER_ID = os.environ["BOT_USER_ID"]

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

rag_system = SupabaseRAGSystem()


def reply_to_post(user_id: str, post_id: str, post_content: str) -> dict:
    """
    Create a comment (reply) on a post.

    Args:
        user_id: UUID of the user posting the comment.
        post_id: UUID of the post being replied to.
        post_content: Text content of the comment.

    Returns:
        The inserted comment record as a dict.

    Raises:
        Exception: If the insert fails.
    """
    res = supabase.table("comments").insert({
        "user_id": user_id,
        "post_id": post_id,
        "content": post_content,
    }).execute()

    if not res.data:
        raise Exception(f"Failed to insert comment: {res}")

    return res.data[0]


def get_comments_for_post(post_id: str) -> list:
    """
    Fetch all comments for a given post, ordered oldest-first.

    Args:
        post_id: UUID of the post.

    Returns:
        List of comment records.
    """
    res = (
        supabase.table("comments")
        .select("id, post_id, user_id, content, created_at")
        .eq("post_id", post_id)
        .order("created_at", desc=False)
        .execute()
    )
    return res.data


def handle_post(post: dict) -> dict:
    """Process a post through RAG and publish a comment reply.

    Args:
        post: Dict with keys 'id', 'title', 'content'.

    Returns:
        The inserted comment record.
    """
    post_id = post["id"]
    title = post.get("title", "")
    content = post.get("content", "")

    logger.info(f"Generating RAG response for post {post_id}")
    result = rag_system.process_query(header=title, content=content)
    answer = result["answer"]

    logger.info(f"Publishing comment on post {post_id}")
    comment = reply_to_post(
        user_id=BOT_USER_ID,
        post_id=post_id,
        post_content=answer,
    )
    return comment
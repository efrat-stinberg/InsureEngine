"""
Supabase RAG API Handler

Handles semantic search and answer generation using Supabase + pgvector.
"""

from supabase import create_client, Client
from openai import OpenAI
import os
from typing import Dict, List, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SupabaseRAGSystem:
    """RAG system for semantic search and answer generation"""

    def __init__(self):
        """Initialize RAG system"""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        openai_api_key = os.getenv('OPENAI_API_KEY')

        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.embeddings_model = OpenAI(api_key=openai_api_key)

        logger.info("✓ SupabaseRAGSystem initialized")

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model="text-embedding-3-small",
                dimensions=1532
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    def search_similar_embeddings(self,query_embedding: List[float]) -> List[Dict[str, Any]]:
        """Search for similar embeddings in Supabase"""
        match_count: int = 5
        similarity_threshold: float = 0.5
        # change uery to string with ',' between numbers
        # vec = "[" + ",".join(str(x) for x in query_embedding) + "]"
        try:
            resp = self.supabase.rpc(
            "match_embeddings_cosine"
            ,
            {     
                "query_embedding": query_embedding,
                "match_threshold": 0.78,
                "match_count": 10
            },
            ).execute()
            matches = resp.data  
            # רשימת תוצאות

            for m in matches:    
                print(m["similarity"], m["text"][:200])

            return matches
           
        except Exception as e:
            logger.error(f"Error searching embeddings: {e}")
            return []

    def build_context_prompt(self, query: str, similar_chunks: List[Dict[str, Any]]) -> str:
        """Build prompt with retrieved context"""
        context_parts = []

        for chunk in similar_chunks:
            context_parts.append(f"""
            Document: {chunk.get('metadata', {}).get('source', 'Unknown')}
            Chunk {chunk.get('chunk_id', 0)}:
            {chunk.get('text', '')}
        """)

        context = "\n---\n".join(context_parts)
        return f"""CONTEXT:\n{context}\n\n QUESTION:\n{query}"""

    def generate_answer(self, prompt: str) -> str:
        """Generate answer using OpenAI"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": """
                        You are an insurance expert assistant.

                        Rules:
                        - Answer based only on provided context
                        - Maintain a friendly and inviting tone of conversation.
                        - You should always make do with the information that is available. If it is missing, provide general or statistical information.
                        - Always offer to contact a direct insurance website for accurate information, including a link.
                        - Use insurance terminology. But make sure it is understandable to everyone.
                        - add more information from this website: https://www.555.co.il/ - it is the most relevant and up-to-date source for insurance information.
                        - focus on statistics and numbers from the provided context.
                        - Add relevant links for cars https://www.555.co.il/car-insurance/ for appartments https://www.555.co.il/home-insurance/ 
                        """},
                    {"role": "user", "content":prompt}
                ],
                
                max_tokens=1000,
                temperature=0.5
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return "I apologize, but I encountered an error while processing your question."

    def process_query(self, header: str, content: str) -> Dict[str, Any]:
        """Main API method: Process query and return answer

        Args:
            header: Query header/title
            content: Query content/body

        Returns:
            Dict with answer and metadata
        """
        try:
            # Combine header and content for embedding
            full_query = f"{header}\n{content}"

            logger.info(f"Processing query: {header[:50]}...")

            # 1. Generate embedding for the query
            query_embedding = self.generate_embedding(full_query)
            logger.info("✓ Generated query embedding")

            # 2. Search for similar content in Supabase
            similar_chunks = self.search_similar_embeddings(
                query_embedding
            )
            logger.info(f"✓ Found {len(similar_chunks)} similar chunks")

            # 3. Build context prompt
            prompt = self.build_context_prompt(content, similar_chunks)
            logger.info("✓ Built context prompt")

            # 4. Generate answer
            answer = self.generate_answer(prompt)
            logger.info("✓ Generated answer")

            return {
                "answer": answer,
                "metadata": {
                    "query_header": header,
                    "query_content": content,
                    "chunks_found": len(similar_chunks),
                    "sources": list(set(
                        chunk.get('metadata', {}).get('source', 'Unknown')
                        for chunk in similar_chunks
                    ))
                }
            }

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "answer": "I apologize, but I encountered an error while processing your question. Please try again.",
                "metadata": {
                    "error": str(e),
                    "query_header": header,
                    "query_content": content
                }
            }


# Example usage (for testing)
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    rag = SupabaseRAGSystem()

    # Test query
    result = rag.process_query(
        header="Question",
        content="במה שונה ביטוח רכב יוקרה מביטוח רכב רגיל?"
    )

    print("Answer:", result["answer"])
    print("Metadata:", result["metadata"])

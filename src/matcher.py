import json
from typing import Any
from PIL import Image
from src.gemini_client import GeminiClient


def get_top_performing_reels_context(repo: Any, user_id: str | None = None, top_k: int = 5) -> str:
    if not repo:
        return ""
    try:
        top_reels = repo.get_top_performing_reels(user_id=user_id, top_k=top_k)
        if not top_reels:
            return ""

        lines = ["\nHISTÓRICO DE REELS DE MAIOR DESEMPENHO DO USUÁRIO (RAG):"]
        for idx, r in enumerate(top_reels, 1):
            views = r.get("views", 0)
            likes = r.get("likes", 0)
            caption = (r.get("caption") or "").replace("\n", " ")[:120]
            lines.append(f"{idx}. [{views} views, {likes} likes] Legenda/Gancho: '{caption}'")

        lines.append("Instrução: Dê preferência a estilos e opções de vídeo que se alinhem com a estrutura desses Reels de alto engajamento.\n")
        return "\n".join(lines)
    except Exception:
        return ""


class Matcher:
    def __init__(self, client: Any):
        self.client = client

    def rank_candidates(
        self,
        reference_description: str,
        candidates: list[dict[str, Any]],
        top_k: int = 3,
        repo: Any = None,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        rag_context = get_top_performing_reels_context(repo, user_id=user_id) if repo else ""

        prompt = f"""
Reference video description: {reference_description}
{rag_context}
Local videos:
"""
        for idx, c in enumerate(candidates, 1):
            vid_id = c.get("id", idx)
            prompt += f"Video ID: {vid_id}\nDescription: {c['description']}\nThemes: {c.get('themes', '')}\nOrientation: {c.get('orientation', '')}\nDuration: {c.get('duration_seconds', 0)}s\n\n"

        prompt += f"""
Rank the {top_k} local videos that best match the reference video in terms of theme, content, style and orientation.
Return valid JSON only, with a field "ranking" containing objects with "video_id" (integer) and "reason" (string).
IMPORTANT: Never use double quotes (") inside the text fields of the JSON (like "reason"); use single quotes (') instead if you need to quote something.
"""
        schema = {
            "type": "object",
            "properties": {
                "ranking": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "video_id": {"type": "integer"},
                            "reason": {"type": "string"},
                        },
                        "required": ["video_id", "reason"],
                    },
                }
            },
            "required": ["ranking"],
        }
        raw = self.client.analyze([], prompt, response_schema=schema)
        data = json.loads(raw) if isinstance(raw, str) else raw
        ranking = data.get("ranking", [])
        
        from datetime import datetime, timezone
        now_utc = datetime.now(timezone.utc)

        # Build map of candidate id/path to base score from LLM ranking
        scored_candidates = []
        for c in candidates:
            # Find candidate's rank position in LLM output
            c_id = c.get("id")
            c_path = c.get("path")
            rank_idx = 999
            for idx, r in enumerate(ranking):
                vid_id = r.get("video_id")
                if vid_id is not None:
                    try:
                        target_id = int(vid_id)
                        if (c_id is not None and int(c_id) == target_id) or (candidates.index(c) + 1) == target_id:
                            rank_idx = idx
                            break
                    except (ValueError, TypeError):
                        pass

            base_score = max(20.0, 100.0 - (rank_idx * 20.0)) if rank_idx < 999 else 10.0

            # Usage & Recency adjustments
            usage_count = int(c.get("usage_count", 0) or 0)
            last_used_at = c.get("last_used_at")

            bonus = 20.0 if usage_count == 0 else 0.0
            freq_penalty = usage_count * 5.0

            recency_penalty = 0.0
            if last_used_at:
                try:
                    dt = datetime.fromisoformat(str(last_used_at).replace("Z", "+00:00"))
                    days_ago = max(0.0, (now_utc - dt).total_seconds() / 86400.0)
                    if days_ago < 7.0:
                        recency_penalty = 30.0 * (7.0 - days_ago) / 7.0
                except Exception:
                    pass

            adjusted_score = base_score + bonus - freq_penalty - recency_penalty
            scored_candidates.append((adjusted_score, c))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        ordered = [item[1] for item in scored_candidates]

        return ordered[:top_k]

    def select_best_video(
        self,
        reference_frames: list[Image.Image],
        top_candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        candidate_info_str = "\n"
        for idx, c in enumerate(top_candidates, 1):
            vid_id = c.get("id", idx)
            candidate_info_str += f"Candidate {idx}: Video ID {vid_id} (representing next {len(c.get('frame_paths', []))} frames)\n"

        prompt = f"""
You are choosing the best local video to replace the visual content of a Reels reference while keeping its audio and text.
Look at the reference frames and the frames of the candidate videos below, then choose the candidate whose visual style, theme and energy match the reference most.

The candidate frames are appended in sequence after the reference frames as follows:{candidate_info_str}

Return valid JSON only with fields "best_video_id" (integer) and "reason" (string).
IMPORTANT: Never use double quotes (") inside the text fields of the JSON (like "reason"); use single quotes (') instead if you need to quote something.
"""
        schema = {
            "type": "object",
            "properties": {
                "best_video_id": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["best_video_id", "reason"],
        }
        images = list(reference_frames)
        for c in top_candidates:
            for fp in c.get("frame_paths", [])[:3]:
                images.append(Image.open(fp))

        raw = self.client.analyze(images, prompt, response_schema=schema)
        data = json.loads(raw) if isinstance(raw, str) else raw
        best_id = data.get("best_video_id")
        
        if best_id is not None:
            try:
                target_best_id = int(best_id)
                for idx, c in enumerate(top_candidates, 1):
                    c_id = c.get("id")
                    if (c_id is not None and int(c_id) == target_best_id) or idx == target_best_id:
                        c["selection_reason"] = data.get("reason", "")
                        return c
            except (ValueError, TypeError):
                pass
                
        # Fallback to first candidate
        return top_candidates[0]

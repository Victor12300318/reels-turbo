import json
from typing import Any
from PIL import Image
from src.gemini_client import GeminiClient


class Matcher:
    def __init__(self, client: GeminiClient):
        self.client = client

    def rank_candidates(
        self,
        reference_description: str,
        candidates: list[dict[str, Any]],
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        prompt = f"""
Reference video description: {reference_description}

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
        
        ordered = []
        for r in ranking:
            vid_id = r.get("video_id")
            if vid_id is not None:
                try:
                    target_id = int(vid_id)
                    for i, c in enumerate(candidates, 1):
                        c_id = c.get("id")
                        if (c_id is not None and int(c_id) == target_id) or i == target_id:
                            ordered.append(c)
                            break
                except (ValueError, TypeError):
                    pass

        # Fallback to candidates in order if nothing matched
        if not ordered:
            return candidates[:top_k]
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

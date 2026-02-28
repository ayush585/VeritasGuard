import asyncio
import base64
from server.agents.base_agent import BaseAgent


class MediaForensicsAgent(BaseAgent):
    def __init__(self):
        super().__init__("MediaForensics", model="mistral-medium-latest")

    def get_instructions(self) -> str:
        return (
            "You are a media forensics expert. Analyze text that may have been extracted "
            "from images via OCR. Look for signs of manipulation, sensationalism, "
            "clickbait patterns, emotional language designed to mislead, and formatting "
            "that suggests forwarded chain messages. "
            "Respond with JSON:\n"
            "{\n"
            '  "manipulation_indicators": ["..."],\n'
            '  "credibility_score": 0.0-1.0,\n'
            '  "content_type": "news|social_media|chain_message|meme|screenshot|unknown",\n'
            '  "red_flags": ["..."],\n'
            '  "analysis": "..."\n'
            "}"
        )

    async def process(self, data: dict) -> dict:
        text = data.get("text", "")
        original_text = data.get("original_text", text)
        image_data = data.get("image_data")

        # If we have raw image bytes, try Pixtral vision analysis
        vision_analysis = ""
        if image_data:
            try:
                b64 = base64.b64encode(image_data).decode()
                response = await asyncio.to_thread(
                    self.client.chat.complete,
                    model="pixtral-large-latest",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                            {"type": "text", "text": (
                                "Analyze this image for signs of manipulation or misinformation. "
                                "Look for: edited text, photoshop artifacts, misleading context, "
                                "sensationalist formatting. Describe what you see."
                            )},
                        ],
                    }],
                )
                vision_analysis = response.choices[0].message.content
            except Exception as e:
                vision_analysis = f"Vision analysis unavailable: {e}"

        # Text-based forensics
        prompt = (
            f"Analyze this text for misinformation indicators:\n\n"
            f"ORIGINAL TEXT: {original_text}\n\n"
            f"ENGLISH TEXT: {text}\n\n"
        )
        if vision_analysis:
            prompt += f"IMAGE ANALYSIS: {vision_analysis}\n\n"
        prompt += "Respond ONLY with JSON per your instructions."

        response = await self._query(prompt)
        result = self._parse_response(response)

        if "credibility_score" not in result:
            result = {
                "manipulation_indicators": [],
                "credibility_score": 0.5,
                "content_type": "unknown",
                "red_flags": [],
                "analysis": response[:500] if response else "Could not complete analysis.",
            }

        return result

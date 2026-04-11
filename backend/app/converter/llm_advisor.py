import base64
import json
import urllib.error
import urllib.request

from app.config import settings
from app.models.result import Region


class LLMColorAdvisor:
    """ローカルLLM（Ollama）を使用した高度な色補正アドバイザー（オプション）"""

    def is_available(self) -> bool:
        """Ollamaサービスが利用可能か確認する。

        Returns:
            利用可能な場合はTrue
        """
        try:
            url = f"{settings.ollama_url}/api/tags"
            with urllib.request.urlopen(url, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def suggest_color_correction(
        self,
        original_path: str,
        converted_path: str,
        diff_regions: list[Region],
    ) -> dict:
        """LLMに色補正の提案を依頼する。

        Args:
            original_path: 元画像のパス
            converted_path: 変換後画像のパス
            diff_regions: 色差が大きい領域のリスト

        Returns:
            色補正プラン（LLMの提案）
        """
        if not self.is_available():
            return {}

        try:
            # 画像をBase64エンコード
            with open(converted_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode()

            region_desc = f"{len(diff_regions)}箇所の色ずれ領域"

            prompt = (
                f"この画像はAI/PSDファイルをJPEGに変換したものです。"
                f"{region_desc}が検出されました。"
                f"色補正の方向性をJSON形式で提案してください。"
                f"応答はJSONのみで: {{\"brightness\": -10~10, \"saturation\": -20~20, "
                f"\"hue_shift\": -30~30, \"contrast\": -10~10}}"
            )

            payload = json.dumps(
                {
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False,
                }
            ).encode()

            req = urllib.request.Request(
                f"{settings.ollama_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=60) as resp:
                response_data = json.loads(resp.read())
                response_text = response_data.get("response", "{}")

                # JSONを抽出
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(response_text[start:end])

        except Exception:
            pass

        return {}

    def apply_llm_correction(self, image_path: str, plan: dict) -> bool:
        """LLMの提案に基づいて色補正を適用する。

        Args:
            image_path: 補正する画像のパス（インプレースで修正）
            plan: LLMの色補正プラン

        Returns:
            補正が適用された場合はTrue
        """
        if not plan:
            return False

        try:
            from wand.image import Image

            with Image(filename=image_path) as img:
                brightness = plan.get("brightness", 0)
                saturation = plan.get("saturation", 0)
                contrast = plan.get("contrast", 0)

                # 明度調整
                if brightness != 0:
                    factor = (100 + brightness) / 100.0
                    img.evaluate(operator="multiply", value=factor)

                # コントラスト調整
                if contrast != 0:
                    img.sigmoidal_contrast(sharpen=contrast > 0, strength=abs(contrast) / 10)

                # 色調・彩度調整（HSL空間で操作）
                if saturation != 0:
                    img.modulate(saturation=100 + saturation)

                img.save(filename=image_path)
                return True

        except Exception:
            return False

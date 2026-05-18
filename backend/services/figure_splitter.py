import cv2
import numpy as np
import json
import os
from PIL import Image
from scipy.spatial import cKDTree
from ultralytics import SAM
from google.genai import types
from unified_rag.config import settings
from unified_rag.gemini_client import get_client
import typing_extensions as typing

MODEL = "gemini-2.5-flash"

class ComponentSchema(typing.TypedDict):
    x: int
    y: int
    is_noise: bool
    label: str

class LayoutResultSchema(typing.TypedDict):
    components: list[ComponentSchema]

class FigureSplitter:
    def __init__(self, model_path="models/mobile_sam.pt"):
        self.api_key = settings.gemini_api_key
        self.model_path = model_path
        self._model = None

    @property
    def model(self):
        if self._model is None:
            print(f"🚀 [FigureSplitter] Loading Mobile SAM from {self.model_path}...")
            self._model = SAM(self.model_path)
        return self._model

    def ask_gemini_centers(self, image_bgr, parent_context=""):
        """
        Uses Gemini-2.5-Flash to identify semantic centers of distinct sub-diagrams.
        Leverages Gemini Structured JSON Output for 100% parse rate.
        """
        if not self.api_key:
            print("⚠️ [FigureSplitter] Gemini API key not set. Skipping centers.")
            return []

        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(image_rgb)

        prompt = (
            "You are an expert technical layout analyzer. Analyze this technical drawing.\n"
            f"Context: {parent_context}\n"
            "Identify the exact center points (x,y) of each distinct machine diagram OR major text instruction block.\n"
            "Return a JSON object containing a 'components' list with details:\n"
            " - 'x': normalized x coordinate (0 to 1000)\n"
            " - 'y': normalized y coordinate (0 to 1000)\n"
            " - 'is_noise': boolean (true if text/label, false if machine diagram)\n"
            " - 'label': short descriptive label"
        )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = get_client().models.generate_content(
                    model=MODEL,
                    contents=[prompt, pil_img],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=LayoutResultSchema,
                        temperature=0.0
                    )
                )

                raw_content = response.text
                if not raw_content:
                    raise ValueError("Gemini returned empty text")

                data = json.loads(raw_content)
                return data.get("components", [])

            except Exception as e:
                print(f"⚠️ [FigureSplitter] Gemini Attempt {attempt+1} failed: {e}")
                import time
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    print(f"❌ [FigureSplitter] All attempts to fetch centers failed.")
                    return []

    def split_image_sam(self, image, parent_context="", min_area=500):
        """
        Full Agentic Pipeline: Gemini Centers -> Voronoi Clustering -> SAM Neural Masking.
        Returns: List of dicts with { 'box': (x,y,w,h), 'crop': image_data, 'label': string }
        """
        h, w = image.shape[:2]
        llm_centers = self.ask_gemini_centers(image, parent_context)

        if not llm_centers:
            return []

        centers_px = []
        is_noise_list = []
        labels_list = []

        for pt in llm_centers:
            cx = max(0, min(w-1, int(pt.get("x", 0) / 1000.0 * w)))
            cy = max(0, min(h-1, int(pt.get("y", 0) / 1000.0 * h)))
            centers_px.append([cy, cx])
            is_noise_list.append(pt.get("is_noise", False))
            labels_list.append(pt.get("label", "Component"))

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            if cv2.boundingRect(c)[2] > 0.8 * w or cv2.boundingRect(c)[3] > 0.8 * h:
                cv2.drawContours(binary, [c], -1, 0, -1)

        points = np.column_stack(np.where(binary > 0))
        if len(points) == 0 or len(centers_px) < 1:
            return []

        tree = cKDTree(np.array(centers_px))
        _, cluster_labels = tree.query(points)

        results = []

        for i in range(len(centers_px)):
            if is_noise_list[i]:
                continue

            cluster_points = points[cluster_labels == i]
            if len(cluster_points) == 0:
                continue

            ymin_v, ymax_v = cluster_points[:, 0].min(), cluster_points[:, 0].max()
            xmin_v, xmax_v = cluster_points[:, 1].min(), cluster_points[:, 1].max()

            try:
                sam_res = self.model(image, bboxes=[xmin_v, ymin_v, xmax_v, ymax_v], retina_masks=True, verbose=False)
                if not sam_res or not sam_res[0].masks:
                    continue

                mask_array = sam_res[0].masks.data[0].cpu().numpy()
                if mask_array.shape[:2] != (h, w):
                    mask_resized = cv2.resize(mask_array, (w, h), interpolation=cv2.INTER_NEAREST)
                else:
                    mask_resized = mask_array

                poly_mask = (mask_resized > 0).astype(np.uint8) * 255
            except Exception as e:
                print(f"⚠️ [FigureSplitter] SAM failed for a component: {e}. Falling back to Voronoi box.")
                poly_mask = np.zeros((h, w), dtype=np.uint8)
                poly_mask[ymin_v:ymax_v, xmin_v:xmax_v] = 255

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
            mask_solid = cv2.dilate(poly_mask, kernel, iterations=1)
            contours, _ = cv2.findContours(mask_solid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            final_mask = np.zeros((h, w), dtype=np.uint8)
            if contours:
                largest = max(contours, key=cv2.contourArea)
                cv2.drawContours(final_mask, [largest], -1, 255, -1)
                bx, by, bw, bh = cv2.boundingRect(largest)
            else:
                bx, by, bw, bh = xmin_v, ymin_v, (xmax_v - xmin_v), (ymax_v - ymin_v)
                final_mask[by:by+bh, bx:bx+bw] = 255

            if bw * bh < min_area:
                continue

            crop_rgba = np.zeros((bh, bw, 4), dtype=np.uint8)
            orig_snippet = image[by:by+bh, bx:bx+bw]
            orig_rgba = cv2.cvtColor(orig_snippet, cv2.COLOR_BGR2BGRA)
            local_mask = final_mask[by:by+bh, bx:bx+bw]
            crop_rgba[local_mask == 255] = orig_rgba[local_mask == 255]

            final_bgr = np.ones((bh, bw, 3), dtype=np.uint8) * 255
            alpha = crop_rgba[:, :, 3] / 255.0
            for c in range(3):
                final_bgr[:, :, c] = (alpha * crop_rgba[:, :, c] + (1 - alpha) * 255).astype(np.uint8)

            results.append({
                "box": (bx, by, bw, bh),
                "crop": final_bgr,
                "label": labels_list[i]
            })

        return results

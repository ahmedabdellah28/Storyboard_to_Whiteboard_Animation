import cv2
import numpy as np
import logging
from typing import List, Tuple, Optional, Callable, Dict, Any
from ..core.stroke import Stroke, StrokeType
from ..core.region import ColorRegion
from ..core.scene import Scene, SceneObject, SceneConfig
from ..core.project import Project, StructureType, PanelStructure
from .edge_extractor import EdgeExtractor
from .stroke_classifier import StrokeClassifier
from .color_processor import ColorProcessor
from .region_extractor import RegionExtractor
from ..planning.object_grouping import MajorObjectGrouper
from .panel_detector import PanelDetector

logger = logging.getLogger(__name__)


class ImageProcessor:
    @staticmethod
    def process(image_bgr: np.ndarray, config: SceneConfig,
                progress_cb: Optional[Callable[[float, str], None]] = None) -> Project:
        """
        Universal processing pipeline (V3 — Fully Dynamic Multi-Panel & Single Scene):
        1. Structural Analysis via PanelDetector (detects 1, 2, 4, 6, 8, 9+ panels or single scenes)
        2. For Storyboard: crop each panel and extract characters/elements at native resolution
        3. For Single Scene: process the full image
        """
        def _report(pct, msg):
            if progress_cb:
                progress_cb(pct, msg)

        _report(5.0, "Analyzing composition & panels...")

        ih, iw = image_bgr.shape[:2]

        # 1. Structural Analysis via PanelDetector
        try:
            detected_project = PanelDetector.detect(image_bgr)
            is_storyboard = detected_project.structure_type.is_storyboard and len(detected_project.panels) >= 2
        except Exception as e:
            logger.warning(f"Error in PanelDetector.detect: {e}")
            is_storyboard = False
            detected_project = Project(structure_type=StructureType.SINGLE_SCENE)

        project = Project(
            structure_type=StructureType.STORYBOARD if is_storyboard else StructureType.SINGLE_SCENE,
            source_image=image_bgr,
            original_width=iw,
            original_height=ih
        )

        if is_storyboard:
            valid_panels = [p for p in detected_project.panels if not p.is_empty]
            if not valid_panels:
                valid_panels = detected_project.panels

            _report(20.0, f"Storyboard detected: {len(valid_panels)} panels. Extracting entities...")
            project.panels = valid_panels

            for p_idx, panel in enumerate(valid_panels):
                p_id = panel.id
                px, py, pw, ph = panel.interior_bbox
                px = max(0, min(iw - 1, px))
                py = max(0, min(ih - 1, py))
                pw = max(1, min(iw - px, pw))
                ph = max(1, min(ih - py, ph))

                p_crop = image_bgr[py:py+ph, px:px+pw]
                if p_crop.size == 0:
                    continue

                raw_entities = ImageProcessor._extract_entities_from_crop(p_crop)

                scene_objs = []
                if raw_entities:
                    for e_idx, ent in enumerate(raw_entities):
                        ebx = int(ent["rel_x"])
                        eby = int(ent["rel_y"])
                        ebw = int(ent["w"])
                        ebh = int(ent["h"])
                        gx = int(px + ebx)
                        gy = int(py + eby)

                        suffix = ent.get("name_suffix", f"Character {e_idx + 1}")
                        name = f"Panel {p_id} - {suffix}"
                        obj = SceneObject(
                            name=name,
                            bbox=(ebx, eby, ebw, ebh),
                            global_bbox=(gx, gy, ebw, ebh),
                            panel_id=p_id,
                            width=ebw,
                            height=ebh,
                            area=int(ent.get("area", ebw * ebh)),
                            crop=ent.get("crop", None)
                        )
                        obj.scene_source_image = image_bgr
                        scene_objs.append(obj)
                else:
                    # Fallback: Whole panel interior is the primary object
                    name = f"Panel {p_id} - Scene"
                    obj = SceneObject(
                        name=name,
                        bbox=(0, 0, pw, ph),
                        global_bbox=(px, py, pw, ph),
                        panel_id=p_id,
                        width=pw,
                        height=ph,
                        area=pw * ph,
                        crop=p_crop
                    )
                    obj.scene_source_image = image_bgr
                    scene_objs.append(obj)

                scene = Scene(
                    config=config,
                    objects=scene_objs,
                    background_color=(255, 255, 255),
                    source_image=p_crop,
                    canvas_width=pw,
                    canvas_height=ph,
                    panel_id=p_id,
                    structure_info="STORYBOARD"
                )
                project.scenes.append(scene)

            project.scenes.sort(key=lambda s: getattr(s, "panel_id", 0))

        else:
            _report(20.0, "Single scene detected. Extracting drawing layers...")
            normalized_img = ImageProcessor.resize_and_pad(
                image_bgr, config.width, config.height
            )
            scene = ImageProcessor._process_single_scene(normalized_img, config)
            scene.structure_info = "SINGLE_SCENE"
            for obj in scene.objects:
                obj.global_bbox = obj.bbox
                obj.scene_source_image = image_bgr
            project.scenes.append(scene)

        _report(100.0, "Ready")
        return project

    @staticmethod
    def process_custom_bboxes(image_bgr: np.ndarray, custom_boxes: List[Dict[str, Any]], config: SceneConfig) -> Project:
        """
        Builds a full Project based on user-drawn / manually annotated bounding boxes.
        Each box is given exact sequential order (1, 2, 3...).
        """
        ih, iw = image_bgr.shape[:2]
        project = Project(
            structure_type=StructureType.STORYBOARD if len(custom_boxes) > 1 else StructureType.SINGLE_SCENE,
            source_image=image_bgr,
            original_width=iw,
            original_height=ih
        )

        panels = []
        for idx, box_info in enumerate(custom_boxes):
            box_id = idx + 1
            bx, by, bw, bh = box_info["bbox"]
            bx = max(0, min(iw - 1, int(round(bx))))
            by = max(0, min(ih - 1, int(round(by))))
            bw = max(2, min(iw - bx, int(round(bw))))
            bh = max(2, min(ih - by, int(round(bh))))

            crop = image_bgr[by:by+bh, bx:bx+bw]
            name = box_info.get("name", f"Element {box_id}")

            panel_struct = PanelStructure(
                id=box_id,
                bbox=(bx, by, bw, bh),
                interior_bbox=(bx, by, bw, bh),
                border_mask=np.zeros((bh, bw), dtype=np.uint8),
                number=box_id,
                index=idx,
                content_score=10.0,
                is_empty=False,
                content_region_image=crop,
                source_image=crop
            )
            panels.append(panel_struct)

            obj = SceneObject(
                name=name,
                bbox=(0, 0, bw, bh),
                global_bbox=(bx, by, bw, bh),
                panel_id=box_id,
                width=bw,
                height=bh,
                area=bw * bh,
                crop=crop
            )
            obj.scene_source_image = image_bgr

            scene = Scene(
                config=config,
                objects=[obj],
                background_color=(255, 255, 255),
                source_image=crop,
                canvas_width=bw,
                canvas_height=bh,
                panel_id=box_id,
                structure_info="CUSTOM_MANUAL"
            )
            project.scenes.append(scene)

        project.panels = panels
        return project

    @staticmethod
    def _extract_entities_from_crop(q_img: np.ndarray, min_entity_area: int = 30) -> List[dict]:
        """Extracts isolated entities/characters from within a panel crop with high precision."""
        qh, qw = q_img.shape[:2]
        gray = cv2.cvtColor(q_img, cv2.COLOR_BGR2GRAY)
        non_white = (gray < 235).astype(np.uint8)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(non_white)

        raw_entities = []
        for label in range(1, num_labels):
            bx = stats[label, cv2.CC_STAT_LEFT]
            by = stats[label, cv2.CC_STAT_TOP]
            bw = stats[label, cv2.CC_STAT_WIDTH]
            bh = stats[label, cv2.CC_STAT_HEIGHT]
            area = stats[label, cv2.CC_STAT_AREA]

            # Exclude outer bounding frame lines
            if (bw < 6 and (bx == 0 or bx + bw >= qw)) or (bh < 6 and (by == 0 or by + bh >= qh)):
                continue
            if bw > 0.85 * qw and bh > 0.85 * qh:
                continue
            if area < min_entity_area:
                continue

            ent_mask = (labels == label).astype(np.uint8) * 255
            ent_crop = np.full((bh, bw, 3), 255, dtype=np.uint8)
            ent_crop_mask = ent_mask[by:by+bh, bx:bx+bw]
            ent_crop[ent_crop_mask > 0] = q_img[by:by+bh, bx:bx+bw][ent_crop_mask > 0]

            raw_entities.append({
                "label": label,
                "rel_x": bx, "rel_y": by,
                "w": bw, "h": bh,
                "center_x": bx + bw / 2.0,
                "center_y": by + bh / 2.0,
                "area": area,
                "crop": ent_crop,
                "mask": ent_crop_mask
            })

        return ImageProcessor._sort_entities_reading_order(raw_entities, q_img=q_img)

    @staticmethod
    def _merge_nearby_punctuation(entities: List[dict], q_img: Optional[np.ndarray] = None, max_gap: int = 14) -> List[dict]:
        """دمج علامات الترقيم والنقاط التابعة لنفس علامة التعجب أو الحرف."""
        if len(entities) <= 1:
            return entities

        merged = []
        used = set()

        for i in range(len(entities)):
            if i in used:
                continue
            cur = dict(entities[i])
            bx1, by1 = cur["rel_x"], cur["rel_y"]
            bx2, by2 = bx1 + cur["w"], by1 + cur["h"]
            has_merged = False

            for j in range(i + 1, len(entities)):
                if j in used:
                    continue
                other = entities[j]
                ox1, oy1 = other["rel_x"], other["rel_y"]
                ox2, oy2 = ox1 + other["w"], oy1 + other["h"]

                x_dist = max(0, max(bx1, ox1) - min(bx2, ox2))
                y_dist = max(0, max(by1, oy1) - min(by2, oy2))

                # دمج النقطة بالخط التابع لها مباشرة
                if x_dist <= 2 and y_dist <= max_gap and cur["area"] < 1500 and other["area"] < 1500:
                    used.add(j)
                    has_merged = True
                    nbx1 = min(bx1, ox1)
                    nby1 = min(by1, oy1)
                    nbx2 = max(bx2, ox2)
                    nby2 = max(by2, oy2)
                    nbw = nbx2 - nbx1
                    nbh = nby2 - nby1

                    bx1, by1, bx2, by2 = nbx1, nby1, nbx2, nby2
                    cur["rel_x"] = nbx1
                    cur["rel_y"] = nby1
                    cur["w"] = nbw
                    cur["h"] = nbh
                    cur["center_x"] = nbx1 + nbw / 2.0
                    cur["center_y"] = nby1 + nbh / 2.0
                    cur["area"] += other["area"]

            if has_merged and q_img is not None:
                cur_crop = q_img[cur["rel_y"]:cur["rel_y"]+cur["h"], cur["rel_x"]:cur["rel_x"]+cur["w"]].copy()
                cur_mask = (cv2.cvtColor(cur_crop, cv2.COLOR_BGR2GRAY) < 235).astype(np.uint8) * 255
                cur["crop"] = cur_crop
                cur["mask"] = cur_mask

            merged.append(cur)
        return merged

    @staticmethod
    def _sort_entities_reading_order(entities: List[dict], q_img: Optional[np.ndarray] = None) -> List[dict]:
        """
        ترتيب وفصل العناصر داخل المربع/اللوحة بدقة متناهية:
        1. الشخصيات المنفصلة وغير المتصلة ببعضها تبقى مستقلة تماماً (Character 1, Character 2).
        2. علامات التعجب وردود الفعل تُضبط بإحكام بكسلي متطابق وتُرسم بعد الشخصية من اليسار لليمين.
        """
        if len(entities) <= 1:
            return entities

        entities = ImageProcessor._merge_nearby_punctuation(entities, q_img=q_img)

        # التحقق من وجود شخصية رئيسية وعلامات تعجب/رد فعل علوية
        max_area = max(e["area"] for e in entities)
        if max_area >= 2000:
            # الشخصيات المنفصلة: الكيانات ذات المساحة المعتبرة (لا تدمج أبداً مع بعضها!)
            main_chars = [e for e in entities if e["area"] >= max(1200, max_area * 0.20)]
            reaction_marks = [e for e in entities if e not in main_chars]

            if reaction_marks:
                sorted_chars = sorted(main_chars, key=lambda e: (e["rel_x"]))
                if q_img is not None:
                    # تجميع كافة علامات التعجب وردود الفعل العلوية وتحديد حوافها البكسلية بدقة عالية
                    min_x = min(e["rel_x"] for e in reaction_marks)
                    min_y = min(e["rel_y"] for e in reaction_marks)
                    max_x = max(e["rel_x"] + e["w"] for e in reaction_marks)
                    max_y = max(e["rel_y"] + e["h"] for e in reaction_marks)
                    gw = max(4, max_x - min_x)
                    gh = max(4, max_y - min_y)

                    raw_crop = q_img[min_y:min_y+gh, min_x:min_x+gw].copy()
                    raw_mask = (cv2.cvtColor(raw_crop, cv2.COLOR_BGR2GRAY) < 235).astype(np.uint8) * 255

                    # إحكام صندوق التحديد على البكسلات النشطة الفعلية
                    act_y, act_x = np.where(raw_mask > 0)
                    if len(act_x) > 0 and len(act_y) > 0:
                        tx1, tx2 = int(act_x.min()), int(act_x.max())
                        ty1, ty2 = int(act_y.min()), int(act_y.max())
                        fin_x = min_x + tx1
                        fin_y = min_y + ty1
                        fin_w = tx2 - tx1 + 1
                        fin_h = ty2 - ty1 + 1
                        fin_crop = raw_crop[ty1:ty2+1, tx1:tx2+1]
                        fin_mask = raw_mask[ty1:ty2+1, tx1:tx2+1]
                    else:
                        fin_x, fin_y, fin_w, fin_h = min_x, min_y, gw, gh
                        fin_crop, fin_mask = raw_crop, raw_mask

                    total_area = sum(e["area"] for e in reaction_marks)

                    reaction_group = {
                        "name_suffix": "Reaction Effect",
                        "rel_x": fin_x,
                        "rel_y": fin_y,
                        "w": fin_w,
                        "h": fin_h,
                        "center_x": fin_x + fin_w / 2.0,
                        "center_y": fin_y + fin_h / 2.0,
                        "area": total_area,
                        "crop": fin_crop,
                        "mask": fin_mask,
                        "is_reaction": True
                    }
                    return sorted_chars + [reaction_group]
                else:
                    sorted_reactions = sorted(reaction_marks, key=lambda e: e["rel_x"])
                    return sorted_chars + sorted_reactions

        import functools

        def compare_entities(a, b):
            ax, ay, aw, ah = a["rel_x"], a["rel_y"], a["w"], a["h"]
            bx, by, bw, bh = b["rel_x"], b["rel_y"], b["w"], b["h"]

            # تداخل المحور الأفقي X
            x_overlap = max(0, min(ax + aw, bx + bw) - max(ax, bx))
            min_w = max(1, min(aw, bw))
            x_overlap_ratio = x_overlap / float(min_w)

            # تداخل المحور الرأسي Y
            y_overlap = max(0, min(ay + ah, by + bh) - max(ay, by))
            min_h = max(1, min(ah, bh))
            y_overlap_ratio = y_overlap / float(min_h)

            # 1. عناصر عمودية في نفس العمود -> الأعلى يسبق الأسفل
            if x_overlap_ratio > 0.30 and y_overlap_ratio < 0.40:
                return -1 if ay < by else 1

            # 2. عناصر أفقية متجاورة -> اليسار يسبق اليمين دائماً
            if y_overlap_ratio > 0.30 and x_overlap_ratio < 0.40:
                return -1 if ax < bx else 1

            # 3. ترتيب شبكي عام
            if (ay + ah * 0.5) + (min_h * 0.5) < (by + bh * 0.5):
                return -1
            elif (by + bh * 0.5) + (min_h * 0.5) < (ay + ah * 0.5):
                return 1
            else:
                return -1 if ax < bx else 1

        return sorted(entities, key=functools.cmp_to_key(compare_entities))

    @staticmethod
    def _process_single_scene(image_bgr: np.ndarray, config: SceneConfig) -> Scene:
        """
        Runs the standard drawing extraction pipeline on a single validated image region.
        Works at the image's NATIVE resolution (no re-resize).
        """
        h, w = image_bgr.shape[:2]

        # Step 1: Color quantization (for ANALYSIS only — not for rendering)
        quantized_bgr, palette, bg_color = ColorProcessor.quantize(image_bgr, config)

        # Step 2: Edge extraction
        raw_strokes = EdgeExtractor.extract(image_bgr, config)

        # Step 3: Stroke classification
        classified_strokes = StrokeClassifier.classify(raw_strokes, image_bgr, quantized_bgr, config)

        # Step 4: Region extraction (masks from quantized, but rendering uses source_image)
        regions = RegionExtractor.extract(quantized_bgr, palette, bg_color, config)

        # Step 5: Major Object Grouping
        major_objects = MajorObjectGrouper.group_into_major_objects(
            classified_strokes, regions, w, h, config
        )

        return Scene(
            config=config,
            objects=major_objects,
            background_color=bg_color,
            source_image=image_bgr,
            canvas_width=w,
            canvas_height=h
        )

    @staticmethod
    def _detect_bg_color(image_bgr: np.ndarray) -> Tuple[int, int, int]:
        """Detect background color from image border pixels."""
        if image_bgr is None or image_bgr.size == 0:
            return (255, 255, 255)

        border_top = image_bgr[0, :]
        border_bottom = image_bgr[-1, :]
        border_left = image_bgr[:, 0]
        border_right = image_bgr[:, -1]
        border_pixels = np.concatenate([border_top, border_bottom, border_left, border_right], axis=0)
        median_bg = np.median(border_pixels, axis=0).astype(np.uint8)
        return (int(median_bg[0]), int(median_bg[1]), int(median_bg[2]))

    @staticmethod
    def resize_and_pad(
        img: np.ndarray,
        target_width: int,
        target_height: int,
        color: Tuple[int, int, int] = None
    ) -> np.ndarray:
        """
        Resizes image preserving aspect ratio and pads borders.
        Auto-detects background color from source borders if not specified.
        """
        h, w = img.shape[:2]

        if color is None:
            color = ImageProcessor._detect_bg_color(img)

        scale = min(target_width / float(w), target_height / float(h))
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))

        interp = cv2.INTER_AREA if scale <= 1.0 else cv2.INTER_LANCZOS4
        resized = cv2.resize(img, (new_w, new_h), interpolation=interp)

        pad_w = target_width - new_w
        pad_h = target_height - new_h
        top = pad_h // 2
        bottom = pad_h - top
        left = pad_w // 2
        right = pad_w - left

        padded = cv2.copyMakeBorder(
            resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color
        )
        return padded

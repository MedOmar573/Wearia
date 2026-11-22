import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

import numpy as np
import joblib

from app.core.config import settings
from app.ai.feature_extraction import extract_appearance_signature
from app.ai.preprocessing import GarmentSegmentation
from app.ai.taxonomy import normalize_clothing_color, normalize_clothing_type

logger = logging.getLogger(__name__)

MEMORY_FILE = settings.AI_MODELS_DIR / "feedback_memory.joblib"
SIGNATURE_VERSION = 2
_MEMORY_CACHE: Optional[List[Dict[str, Any]]] = None


class ActiveLearningManager:
    @staticmethod
    def load_memory() -> List[Dict[str, Any]]:
        global _MEMORY_CACHE
        if _MEMORY_CACHE is not None:
            return _MEMORY_CACHE

        if MEMORY_FILE.exists():
            try:
                loaded = joblib.load(MEMORY_FILE)
                if isinstance(loaded, list):
                    # Ne conserver que les entrées v2 L2-normalisées (les anciennes v1 non normalisées
                    # produisaient des faux positifs systématiques à sim > 0.95)
                    v2_entries = [
                        e for e in loaded
                        if isinstance(e, dict) and e.get("signature_version") == SIGNATURE_VERSION
                    ]
                    if len(v2_entries) != len(loaded):
                        logger.info(
                            f"[ActiveLearning] Ignoré {len(loaded) - len(v2_entries)} entrées héritées (v1 non normalisées)."
                        )
                    _MEMORY_CACHE = v2_entries
                else:
                    _MEMORY_CACHE = []
            except Exception as e:
                logger.error(f"[ActiveLearning] Erreur chargement feedback_memory: {e}")
                _MEMORY_CACHE = []
        else:
            _MEMORY_CACHE = []
        return _MEMORY_CACHE

    @staticmethod
    def save_memory(memory: List[Dict[str, Any]]) -> None:
        global _MEMORY_CACHE
        _MEMORY_CACHE = memory
        try:
            settings.AI_MODELS_DIR.mkdir(parents=True, exist_ok=True)
            joblib.dump(memory, MEMORY_FILE)
        except Exception as e:
            logger.error(f"[ActiveLearning] Erreur sauvegarde feedback_memory: {e}")

    @staticmethod
    def reset_memory() -> None:
        """Réinitialise proprement le cache d'apprentissage actif."""
        ActiveLearningManager.save_memory([])

    @staticmethod
    def record_feedback(
        image_path: str,
        category_name: str,
        type_id: int,
        color_name: str,
        color_id: int,
    ) -> bool:
        """
        Enregistre la confirmation/correction utilisateur avec une signature multi-modale
        strictement L2-normalisée (forme HOG + histogramme couleur LAB + vignette).
        """
        p = Path(image_path)
        if not p.exists():
            return False

        try:
            sig = extract_appearance_signature(str(p))
            if sig is None:
                return False

            canonical_cat = normalize_clothing_type(category_name)
            canonical_col = normalize_clothing_color(color_name)

            memory = ActiveLearningManager.load_memory()

            sample = {
                "signature_version": SIGNATURE_VERSION,
                "hog": sig["hog"],
                "color_hist": sig["color_hist"],
                "thumb": sig["thumb"],
                "category": canonical_cat,
                "type_id": type_id,
                "color": canonical_col,
                "color_id": color_id,
                "filename": p.name,
            }

            # Remplacer l'entrée existante si même fichier
            memory = [m for m in memory if m.get("filename") != p.name]
            memory.append(sample)
            if len(memory) > 500:
                memory = memory[-500:]

            ActiveLearningManager.save_memory(memory)
            logger.info(
                f"[ActiveLearning] Feedback v2 enregistré : '{canonical_cat}' ({canonical_col}) - {p.name}"
            )
            return True
        except Exception as e:
            logger.error(f"[ActiveLearning] Erreur enregistrement feedback : {e}")
            return False

    @staticmethod
    def find_matching_memory(
        image_path: str,
        hog_threshold: float = 0.90,
        color_threshold: float = 0.92,
        thumb_threshold: float = 0.88,
        segmentation: Optional[GarmentSegmentation] = None,
    ) -> Optional[Tuple[Dict[str, Any], float]]:
        """
        Recherche si l'image courante correspond réellement à un vêtement déjà validé
        (correspondance conjointe de la forme, de la distribution couleur et de la vignette).
        """
        memory = ActiveLearningManager.load_memory()
        if not memory:
            return None

        p = Path(image_path)
        if segmentation is None and not p.exists():
            return None

        try:
            q_sig = extract_appearance_signature(str(p), segmentation=segmentation)
            if q_sig is None:
                return None

            best_match = None
            best_score = -1.0
            best_details = (0.0, 0.0, 0.0)

            for entry in memory:
                if entry.get("signature_version") != SIGNATURE_VERSION:
                    continue
                e_hog = entry.get("hog")
                e_col = entry.get("color_hist")
                e_thb = entry.get("thumb")
                if e_hog is None or e_col is None or e_thb is None:
                    continue

                hog_sim = float(np.dot(q_sig["hog"], e_hog))
                col_sim = float(np.dot(q_sig["color_hist"], e_col))
                thb_sim = float(np.dot(q_sig["thumb"], e_thb))

                if hog_sim >= hog_threshold and col_sim >= color_threshold and thb_sim >= thumb_threshold:
                    combined = 0.45 * hog_sim + 0.30 * col_sim + 0.25 * thb_sim
                    if combined > best_score:
                        best_score = combined
                        best_match = entry
                        best_details = (hog_sim, col_sim, thb_sim)

            if best_match is not None:
                logger.info(
                    f"[ActiveLearning] Correspondance validée : '{best_match['category']}' / '{best_match['color']}' "
                    f"(score={best_score:.3f}, hog={best_details[0]:.3f}, col={best_details[1]:.3f}, thb={best_details[2]:.3f})"
                )
                return best_match, best_score

            return None
        except Exception as e:
            logger.error(f"[ActiveLearning] Erreur recherche mémoire : {e}")
            return None

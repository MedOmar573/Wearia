import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import numpy as np
import joblib
from sklearn.metrics.pairwise import cosine_similarity
from app.core.config import settings
from app.ai.feature_extraction import extract_advanced_features

logger = logging.getLogger(__name__)

MEMORY_FILE = settings.AI_MODELS_DIR / "feedback_memory.joblib"
_MEMORY_CACHE: Optional[List[Dict[str, Any]]] = None

class ActiveLearningManager:
    @staticmethod
    def load_memory() -> List[Dict[str, Any]]:
        global _MEMORY_CACHE
        if _MEMORY_CACHE is not None:
            return _MEMORY_CACHE

        if MEMORY_FILE.exists():
            try:
                _MEMORY_CACHE = joblib.load(MEMORY_FILE)
                if not isinstance(_MEMORY_CACHE, list):
                    _MEMORY_CACHE = []
            except Exception as e:
                logger.error(f"Erreur chargement feedback_memory: {e}")
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
            logger.error(f"Erreur sauvegarde feedback_memory: {e}")

    @staticmethod
    def record_feedback(
        image_path: str,
        category_name: str,
        type_id: int,
        color_name: str,
        color_id: int
    ) -> bool:
        """
        Enregistre la correction / confirmation de l'utilisateur.
        L'IA mémorise les caractéristiques visuelles exactes de l'image
        pour ne plus jamais refaire l'erreur sur cette pièce ou des pièces similaires.
        """
        p = Path(image_path)
        if not p.exists():
            return False

        try:
            feats = extract_advanced_features(str(p))
            if feats is None or np.all(feats == 0):
                return False

            memory = ActiveLearningManager.load_memory()

            # Vérifier si cet exemple existe déjà pour le mettre à jour
            sample = {
                "features": feats.flatten(),
                "category": category_name,
                "type_id": type_id,
                "color": color_name,
                "color_id": color_id,
                "filename": p.name
            }

            # Garder un historique des 500 dernières pièces apprises
            memory.append(sample)
            if len(memory) > 500:
                memory = memory[-500:]

            ActiveLearningManager.save_memory(memory)
            logger.info(f"Apprentissage IA réussi pour '{category_name}' ({color_name}) - fichier: {p.name}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'apprentissage feedback : {e}")
            return False

    @staticmethod
    def find_matching_memory(
        image_path: str,
        threshold: float = 0.85
    ) -> Optional[Tuple[Dict[str, Any], float]]:
        """
        Recherche si l'image courante correspond à un vêtement précédemment corrigé / confirmé.
        Si la similarité cosinus dépasse le seuil, l'IA privilégie l'apprentissage de l'utilisateur.
        """
        memory = ActiveLearningManager.load_memory()
        if not memory:
            return None

        p = Path(image_path)
        if not p.exists():
            return None

        try:
            query_feats = extract_advanced_features(str(p))
            if query_feats is None or np.all(query_feats == 0):
                return None

            q_vec = query_feats.reshape(1, -1)
            best_match = None
            best_sim = -1.0

            for entry in memory:
                entry_vec = np.array(entry["features"]).reshape(1, -1)
                sim = float(cosine_similarity(q_vec, entry_vec)[0][0])
                if sim > best_sim:
                    best_sim = sim
                    best_match = entry

            if best_match is not None and best_sim >= threshold:
                logger.info(f"Active learning match trouvé ! Catégorie apprise: {best_match['category']} (sim: {best_sim:.2f})")
                return best_match, best_sim

            return None
        except Exception as e:
            logger.error(f"Erreur lors de la recherche active learning : {e}")
            return None

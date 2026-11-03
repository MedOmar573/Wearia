import numpy as np
import cv2
from skimage.feature import hog

def extract_advanced_features(image_path_or_array, target_size=(128, 128)) -> np.ndarray:
    """
    Extrait un vecteur complet de descripteurs visuels pour la classification de vêtements :
    1. Descripteurs structurels HOG (Histogram of Oriented Gradients)
    2. Descripteur de texture et maille (Laplacien / variance locale pour 'Pull' vs 'Chemise')
    3. Descripteur de patte de boutonnage centrale (Sobel vertical pour 'Chemise' vs 'Pull')
    4. Ratios géométriques (Aspect Ratio pour 'Bas' / 'Chaussures' vs 'Hauts')
    """
    try:
        if isinstance(image_path_or_array, str):
            image = cv2.imread(image_path_or_array)
        else:
            image = image_path_or_array

        if image is None:
            return np.zeros((1, 1776), dtype=np.float32)

        # 1. Ratios géométriques sur l'image d'origine
        orig_h, orig_w = image.shape[:2]
        aspect_ratio = orig_h / max(orig_w, 1)

        # Redimensionnement uniforme
        resized = cv2.resize(image, target_size, interpolation=cv2.INTER_AREA)
        if len(resized.shape) == 3:
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        else:
            gray = resized

        # 2. HOG sur image 64x64 pour conserver 1764 dimensions standard
        gray_64 = cv2.resize(gray, (64, 64), interpolation=cv2.INTER_AREA)
        hog_feats = hog(
            gray_64,
            orientations=9,
            pixels_per_cell=(8, 8),
            cells_per_block=(2, 2),
            block_norm='L2-Hys',
            visualize=False
        ).flatten()

        # 3. Analyse du torse central (pour distinguer Pull en maille vs Chemise à boutons)
        # Zone centrale du vêtement (colonne du milieu)
        h, w = gray.shape
        center_col = gray[int(h * 0.2):int(h * 0.8), int(w * 0.42):int(w * 0.58)]
        sobel_x = cv2.Sobel(center_col, cv2.CV_64F, 1, 0, ksize=3)
        placket_energy = float(np.mean(np.abs(sobel_x))) # Élevé pour chemise (boutons verticaux), faible pour pull

        # 4. Texture et maille (Pull vs T-shirt lisse)
        torso_patch = gray[int(h * 0.3):int(h * 0.7), int(w * 0.3):int(w * 0.7)]
        laplacian_var = float(cv2.Laplacian(torso_patch, cv2.CV_64F).var()) # Élevé pour pull en maille côtelée

        # 5. Profils de gradients horizontaux vs verticaux
        grad_x = np.mean(np.abs(cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)))
        grad_y = np.mean(np.abs(cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)))

        # 6. Répartition spatiale haut/bas
        upper_mass = float(np.mean(gray[:h//2, :]))
        lower_mass = float(np.mean(gray[h//2:, :]))
        mass_ratio = (upper_mass + 1e-5) / (lower_mass + 1e-5)

        # 7. Présence d'un col triangulaire pointu (Chemise)
        collar_zone = gray[int(h * 0.08):int(h * 0.28), int(w * 0.3):int(w * 0.7)]
        collar_grad = float(np.mean(np.abs(cv2.Sobel(collar_zone, cv2.CV_64F, 1, 1, ksize=3))))

        # Caractéristiques complémentaires (12 dimensions supplémentaires)
        extra_feats = np.array([
            aspect_ratio,
            placket_energy,
            laplacian_var,
            grad_x,
            grad_y,
            mass_ratio,
            collar_grad,
            float(np.std(gray)),
            float(np.mean(gray)),
            float(np.percentile(gray, 25)),
            float(np.percentile(gray, 75)),
            float(np.max(gray) - np.min(gray))
        ], dtype=np.float32)

        # Concaténation totale : 1764 (HOG) + 12 (Extra) = 1776 dimensions
        full_vector = np.concatenate([hog_feats, extra_feats])
        return full_vector.reshape(1, -1)

    except Exception as e:
        return np.zeros((1, 1776), dtype=np.float32)

def extract_hog_features(image_path_or_array, target_size=(64, 64)) -> np.ndarray:
    """Rétrocompatibilité : appelle extract_advanced_features."""
    return extract_advanced_features(image_path_or_array)

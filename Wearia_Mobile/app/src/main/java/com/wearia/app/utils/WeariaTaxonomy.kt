package com.wearia.app.utils

import com.wearia.app.data.remote.dto.CouleurResponse
import com.wearia.app.data.remote.dto.TypeVetementResponse
import java.text.Normalizer

/**
 * Référentiel unique côté mobile aligné avec wearia_backend/app/ai/taxonomy.py.
 * Standardise les types de vêtements et les couleurs afin d'éviter tout décalage
 * de casse, d'accents ou de collision par sous-chaîne ("Bleu" vs "Bleu Marine").
 */
object WeariaTaxonomy {

    enum class ClothingType(val label: String) {
        CHEMISE("Chemise"),
        TSHIRT("T-Shirt"),
        POLO("Polo"),
        PULL("Pull"),
        SWEAT("Sweat"),
        JEAN("Jean"),
        PANTALON("Pantalon"),
        SHORT("Short"),
        JUPE("Jupe"),
        ROBE("Robe"),
        VESTE("Veste"),
        MANTEAU("Manteau"),
        BASKETS("Baskets"),
        BOTTES("Bottes"),
        CHAUSSURES_VILLE("Chaussures de ville"),
        SAC("Sac"),
        CHAPEAU("Chapeau")
    }

    enum class ClothingColor(val label: String, val hex: String) {
        NOIR("Noir", "#1F1E1D"),
        BLANC("Blanc", "#FFFFFF"),
        GRIS("Gris", "#9E9E9E"),
        BLEU_MARINE("Bleu Marine", "#1B2E4B"),
        BLEU("Bleu", "#21759B"),
        BEIGE("Beige", "#D8C7B5"),
        SABLE("Sable", "#E6DAC8"),
        MARRON("Marron", "#6D4C3D"),
        MARRON_FONCE("Marron Foncé", "#423229"),
        VERT("Vert", "#2E6047"),
        ROUGE("Rouge", "#C63D36"),
        JAUNE("Jaune", "#ECAE28"),
        JAUNE_CLAIR("Jaune Clair", "#F8D548"),
        CORAIL("Corail", "#D94A3D"),
        ROSE("Rose", "#F3B6C2"),
        ORANGE("Orange", "#E56A26"),
        VIOLET("Violet", "#6C47FF")
    }

    private val typeAliases = mapOf(
        "chemise" to ClothingType.CHEMISE.label,
        "shirt" to ClothingType.CHEMISE.label,
        "t-shirt" to ClothingType.TSHIRT.label,
        "tshirt" to ClothingType.TSHIRT.label,
        "t shirt" to ClothingType.TSHIRT.label,
        "polo" to ClothingType.POLO.label,
        "pull" to ClothingType.PULL.label,
        "pullover" to ClothingType.PULL.label,
        "tricot" to ClothingType.PULL.label,
        "sweat" to ClothingType.SWEAT.label,
        "hoodie" to ClothingType.SWEAT.label,
        "jean" to ClothingType.JEAN.label,
        "jeans" to ClothingType.JEAN.label,
        "pantalon" to ClothingType.PANTALON.label,
        "chino" to ClothingType.PANTALON.label,
        "short" to ClothingType.SHORT.label,
        "jupe" to ClothingType.JUPE.label,
        "robe" to ClothingType.ROBE.label,
        "veste" to ClothingType.VESTE.label,
        "blazer" to ClothingType.VESTE.label,
        "bomber" to ClothingType.VESTE.label,
        "manteau" to ClothingType.MANTEAU.label,
        "baskets" to ClothingType.BASKETS.label,
        "basket" to ClothingType.BASKETS.label,
        "sneakers" to ClothingType.BASKETS.label,
        "bottes" to ClothingType.BOTTES.label,
        "botte" to ClothingType.BOTTES.label,
        "chaussures de ville" to ClothingType.CHAUSSURES_VILLE.label,
        "derbies" to ClothingType.CHAUSSURES_VILLE.label,
        "sweatshirt" to ClothingType.SWEAT.label,
        "sweat a capuche" to ClothingType.SWEAT.label,
        "veste en jean" to ClothingType.VESTE.label,
        "blouson" to ClothingType.VESTE.label,
        "doudoune" to ClothingType.MANTEAU.label,
        "trench" to ClothingType.MANTEAU.label,
        "parka" to ClothingType.MANTEAU.label,
        "sac" to ClothingType.SAC.label,
        "sacs" to ClothingType.SAC.label,
        "sac a main" to ClothingType.SAC.label,
        "sac a dos" to ClothingType.SAC.label,
        "bag" to ClothingType.SAC.label,
        "handbag" to ClothingType.SAC.label,
        "cabas" to ClothingType.SAC.label,
        "pochette" to ClothingType.SAC.label,
        "chapeau" to ClothingType.CHAPEAU.label,
        "chapeaux" to ClothingType.CHAPEAU.label,
        "casquette" to ClothingType.CHAPEAU.label,
        "bonnet" to ClothingType.CHAPEAU.label,
        "hat" to ClothingType.CHAPEAU.label,
        "cap" to ClothingType.CHAPEAU.label,
        "beanie" to ClothingType.CHAPEAU.label,
        "bob" to ClothingType.CHAPEAU.label,
        "fedora" to ClothingType.CHAPEAU.label
    )

    private val colorAliases = mapOf(
        "noir" to ClothingColor.NOIR.label,
        "black" to ClothingColor.NOIR.label,
        "blanc" to ClothingColor.BLANC.label,
        "white" to ClothingColor.BLANC.label,
        "gris" to ClothingColor.GRIS.label,
        "grey" to ClothingColor.GRIS.label,
        "gray" to ClothingColor.GRIS.label,
        "bleu marine" to ClothingColor.BLEU_MARINE.label,
        "navy" to ClothingColor.BLEU_MARINE.label,
        "bleu" to ClothingColor.BLEU.label,
        "blue" to ClothingColor.BLEU.label,
        "beige" to ClothingColor.BEIGE.label,
        "sable" to ClothingColor.SABLE.label,
        "marron" to ClothingColor.MARRON.label,
        "brown" to ClothingColor.MARRON.label,
        "marron fonce" to ClothingColor.MARRON_FONCE.label,
        "vert" to ClothingColor.VERT.label,
        "green" to ClothingColor.VERT.label,
        "rouge" to ClothingColor.ROUGE.label,
        "red" to ClothingColor.ROUGE.label,
        "jaune" to ClothingColor.JAUNE.label,
        "yellow" to ClothingColor.JAUNE.label,
        "jaune clair" to ClothingColor.JAUNE_CLAIR.label,
        "corail" to ClothingColor.CORAIL.label,
        "rose" to ClothingColor.ROSE.label,
        "pink" to ClothingColor.ROSE.label,
        "orange" to ClothingColor.ORANGE.label,
        "violet" to ClothingColor.VIOLET.label,
        "purple" to ClothingColor.VIOLET.label
    )

    fun normalizeKey(value: String?): String {
        if (value.isNullOrBlank()) return ""
        val normalized = Normalizer.normalize(value.trim().lowercase(), Normalizer.Form.NFD)
        return normalized.replace(Regex("\\p{InCombiningDiacriticalMarks}+"), "")
    }

    fun normalizeType(raw: String?): String {
        val key = normalizeKey(raw)
        return typeAliases[key] ?: (raw?.trim() ?: "")
    }

    fun normalizeColor(raw: String?): String {
        val key = normalizeKey(raw)
        return colorAliases[key] ?: (raw?.trim() ?: "")
    }

    fun findMatchingTypeIndex(
        types: List<TypeVetementResponse>,
        suggestedTypeId: Int,
        predictedCategory: String?
    ): Int {
        if (types.isEmpty()) return -1
        if (suggestedTypeId > 0) {
            val byId = types.indexOfFirst { it.id == suggestedTypeId }
            if (byId != -1) return byId
        }
        val canonicalKey = normalizeKey(normalizeType(predictedCategory))
        if (canonicalKey.isNotEmpty()) {
            val exact = types.indexOfFirst { normalizeKey(it.nom) == canonicalKey }
            if (exact != -1) return exact
        }
        return -1
    }

    fun findMatchingColorIndex(
        colors: List<CouleurResponse>,
        suggestedColorId: Int,
        predictedColor: String?
    ): Int {
        if (colors.isEmpty()) return -1
        if (suggestedColorId > 0) {
            val byId = colors.indexOfFirst { it.id == suggestedColorId }
            if (byId != -1) return byId
        }
        val canonicalKey = normalizeKey(normalizeColor(predictedColor))
        if (canonicalKey.isNotEmpty()) {
            val exact = colors.indexOfFirst { normalizeKey(it.nom) == canonicalKey }
            if (exact != -1) return exact
        }
        return -1
    }
}

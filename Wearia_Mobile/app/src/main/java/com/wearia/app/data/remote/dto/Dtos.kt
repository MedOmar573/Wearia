package com.wearia.app.data.remote.dto

import com.google.gson.annotations.SerializedName

// =================== AUTH ===================
data class RegisterRequest(
    val nom: String,
    val email: String,
    val password: String
)

data class LoginRequest(
    val email: String,
    val password: String
)

data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String
)

// =================== USER ===================
data class UserResponse(
    val id: Int,
    val nom: String,
    val email: String,
    val genre: String?,
    val ville: String,
    @SerializedName("hauteurCm") val hauteurCm: Int?,
    @SerializedName("poidsKg") val poidsKg: Float?,
    @SerializedName("tourEpaules") val tourEpaules: Float?,
    @SerializedName("tourPoitrine") val tourPoitrine: Float?,
    @SerializedName("tourTaille") val tourTaille: Float?,
    @SerializedName("tourHanches") val tourHanches: Float?,
    @SerializedName("tailleVestimentaire") val tailleVestimentaire: String?,
    @SerializedName("coupePreferee") val coupePreferee: String?,
    @SerializedName("preferences_couleur") val preferencesCouleur: List<PreferenceCouleurResponse> = emptyList(),
    @SerializedName("preferences_style") val preferencesStyle: List<PreferenceStyleResponse> = emptyList()
)

data class UserUpdateRequest(
    val nom: String? = null,
    val genre: String? = null,
    val ville: String? = null,
    @SerializedName("hauteurCm") val hauteurCm: Int? = null,
    @SerializedName("poidsKg") val poidsKg: Float? = null,
    @SerializedName("tourEpaules") val tourEpaules: Float? = null,
    @SerializedName("tourPoitrine") val tourPoitrine: Float? = null,
    @SerializedName("tourTaille") val tourTaille: Float? = null,
    @SerializedName("tourHanches") val tourHanches: Float? = null,
    @SerializedName("tailleVestimentaire") val tailleVestimentaire: String? = null,
    @SerializedName("coupePreferee") val coupePreferee: String? = null
)

// =================== REFERENTIALS ===================
data class CategorieResponse(val id: Int, val nom: String)

data class TypeVetementResponse(
    val id: Int,
    val nom: String,
    @SerializedName("genreCible") val genreCible: String,
    @SerializedName("estCoucheSuperieure") val estCoucheSuperieure: Boolean,
    @SerializedName("categorie_id") val categorieId: Int
)

data class CouleurResponse(val id: Int, val nom: String, @SerializedName("codeHex") val codeHex: String)

data class StyleVestimentaireResponse(val id: Int, val libelle: String)

data class PreferenceCouleurResponse(
    val id: Int,
    val couleur: CouleurResponse,
    @SerializedName("typePreference") val typePreference: String
)

data class ColorPreferencesBatchRequest(
    @SerializedName("liked_color_ids") val likedColorIds: List<Int> = emptyList(),
    @SerializedName("avoided_color_ids") val avoidedColorIds: List<Int> = emptyList()
)

data class PreferenceStyleResponse(
    val id: Int,
    val style: StyleVestimentaireResponse,
    @SerializedName("typePreference") val typePreference: String
)

data class StylePreferencesBatchRequest(
    @SerializedName("style_ids") val styleIds: List<Int> = emptyList()
)

// =================== VÊTEMENT ===================
data class VetementResponse(
    val id: Int,
    val nom: String,
    @SerializedName("photoUrl") val photoUrl: String,
    val matiere: String?,
    val coupe: String,
    val saison: String,
    @SerializedName("estThermique") val estThermique: Boolean,
    @SerializedName("estImpermeable") val estImpermeable: Boolean,
    val statut: String,
    @SerializedName("type_vetement") val typeVetement: TypeVetementResponse,
    val couleur: CouleurResponse,
    @SerializedName("style_vestimentaire") val styleVestimentaire: StyleVestimentaireResponse?
)

data class VetementCreateRequest(
    val nom: String,
    @SerializedName("photoUrl") val photoUrl: String,
    val matiere: String? = null,
    val coupe: String = "REGULIERE",
    val saison: String = "TOUTE_SAISON",
    @SerializedName("estThermique") val estThermique: Boolean = false,
    @SerializedName("estImpermeable") val estImpermeable: Boolean = false,
    val statut: String = "DISPONIBLE",
    @SerializedName("type_vetement_id") val typeVetementId: Int,
    @SerializedName("couleur_id") val couleurId: Int,
    @SerializedName("style_id") val styleId: Int? = null
)

data class VetementUpdateRequest(
    val statut: String? = null,
    val nom: String? = null,
    val matiere: String? = null,
    val coupe: String? = null,
    @SerializedName("type_vetement_id") val typeVetementId: Int? = null,
    @SerializedName("couleur_id") val couleurId: Int? = null
)

// =================== CLASSIFICATION IA ===================
data class ClassifyResponse(
    val category: String,
    val color: String,
    val confidence: Float,
    @SerializedName("image_url") val imageUrl: String,
    @SerializedName("color_hex") val colorHex: String?,
    @SerializedName("suggested_type_id") val suggestedTypeId: Int?,
    @SerializedName("suggested_color_id") val suggestedColorId: Int?,
    val name: String? = null,
    val matiere: String? = null,
    val coupe: String? = null,
    val saison: String? = null,
    @SerializedName("est_thermique") val estThermique: Boolean? = null,
    @SerializedName("est_impermeable") val estImpermeable: Boolean? = null,
    @SerializedName("style_id") val styleId: Int? = null,
    @SerializedName("style_name") val styleName: String? = null
)

// =================== PLANNING ===================
data class RoutineHebdomadaireRequest(
    @SerializedName("jourSemaine") val jourSemaine: String,
    val occasion: String,
    @SerializedName("estActive") val estActive: Boolean = true
)

data class RoutineHebdomadaireResponse(
    val id: Int,
    @SerializedName("jourSemaine") val jourSemaine: String,
    val occasion: String,
    @SerializedName("estActive") val estActive: Boolean
)

data class EvenementRequest(
    val titre: String,
    val date: String, // ISO format: "2024-11-01"
    val occasion: String
)

data class EvenementResponse(
    val id: Int,
    val titre: String,
    val date: String,
    val occasion: String
)

// =================== TENUES & RECOMMANDATIONS ===================
data class RecommendationRequest(
    val occasion: String? = null,
    @SerializedName("dateCible") val dateCible: String? = null,
    val temperature: Float? = null,
    val precipitations: Boolean? = null
)

data class OutfitItemSimple(
    val id: Int,
    val name: String,
    val category: String?,
    val color: String?,
    @SerializedName("image_url") val imageUrl: String?
)

data class RecommendationResponse(
    @SerializedName("outfit_id") val outfitId: Int,
    val occasion: String,
    val temperature: Float?,
    val weather: String?,
    val items: List<OutfitItemSimple>,
    val score: Int,
    val explanation: String
)

data class TenueResponse(
    val id: Int,
    val occasion: String,
    @SerializedName("temperatureCelsius") val temperatureCelsius: Float?,
    val precipitations: Boolean,
    @SerializedName("descriptionMeteo") val descriptionMeteo: String?,
    val explication: String?,
    @SerializedName("scoreCompatibilite") val scoreCompatibilite: Int,
    @SerializedName("estFavorite") val estFavorite: Boolean,
    val vetements: List<VetementResponse>,
    val feedback: FeedbackResponse?
)

data class FeedbackRequest(
    val appreciation: String,
    @SerializedName("motifRejet") val motifRejet: String? = null
)

data class FeedbackResponse(
    val id: Int,
    val appreciation: String,
    @SerializedName("motifRejet") val motifRejet: String?,
    @SerializedName("dateFeedback") val dateFeedback: String
)

// =================== SHOPPING ===================
data class ArticleCatalogueResponse(
    val id: Int,
    val nom: String,
    @SerializedName("imageUrl") val imageUrl: String,
    @SerializedName("lienAchat") val lienAchat: String?,
    val prix: Float,
    val vendeur: String,
    @SerializedName("taillesDisponibles") val taillesDisponibles: String,
    @SerializedName("type_vetement") val typeVetement: TypeVetementResponse,
    val couleur: CouleurResponse
)


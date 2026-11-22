package com.wearia.app.data.remote

import com.wearia.app.data.remote.dto.*
import okhttp3.MultipartBody
import retrofit2.Response
import retrofit2.http.*

/**
 * Interface Retrofit : contrat complet de toutes les routes de l'API FastAPI Wearia.
 * Chaque route correspond à une route documentée dans le Swagger du backend.
 */
interface ApiService {

    // =================== AUTH & OTP ===================
    @POST("auth/register")
    suspend fun register(@Body request: RegisterRequest): Response<AuthStepResponse>

    @POST("auth/login")
    suspend fun login(@Body request: LoginRequest): Response<AuthStepResponse>

    @POST("auth/verify-otp")
    suspend fun verifyOtp(@Body request: VerifyOtpRequest): Response<TokenResponse>

    @POST("auth/resend-otp")
    suspend fun resendOtp(@Body request: ResendOtpRequest): Response<Map<String, Any>>

    // =================== PROFIL ===================
    @GET("users/me")
    suspend fun getProfile(@Header("Authorization") token: String): Response<UserResponse>

    @PUT("users/me")
    suspend fun updateProfile(
        @Header("Authorization") token: String,
        @Body request: UserUpdateRequest
    ): Response<UserResponse>

    @PUT("users/me/preferences/colors/batch")
    suspend fun updateColorPreferences(
        @Header("Authorization") token: String,
        @Body request: ColorPreferencesBatchRequest
    ): Response<List<PreferenceCouleurResponse>>

    @PUT("users/me/preferences/styles/batch")
    suspend fun updateStylePreferences(
        @Header("Authorization") token: String,
        @Body request: StylePreferencesBatchRequest
    ): Response<List<PreferenceStyleResponse>>

    @DELETE("users/me")
    suspend fun deleteAccount(@Header("Authorization") token: String): Response<Unit>

    // =================== RÉFÉRENTIELS ===================
    @GET("referentials/categories")
    suspend fun getCategories(@Query("genre") genre: String? = null): Response<List<CategorieResponse>>

    @GET("referentials/types")
    suspend fun getTypes(@Query("genre") genre: String? = null): Response<List<TypeVetementResponse>>

    @GET("referentials/colors")
    suspend fun getColors(): Response<List<CouleurResponse>>

    @GET("referentials/styles")
    suspend fun getStyles(): Response<List<StyleVestimentaireResponse>>

    // =================== DRESSING (VÊTEMENTS) ===================
    @GET("clothes")
    suspend fun getClothes(
        @Header("Authorization") token: String,
        @Query("categorie_id") categorieId: Int? = null,
        @Query("couleur_id") couleurId: Int? = null,
        @Query("statut") statut: String? = null,
        @Query("search") search: String? = null
    ): Response<List<VetementResponse>>

    @POST("clothes")
    suspend fun addClothing(
        @Header("Authorization") token: String,
        @Body request: VetementCreateRequest
    ): Response<VetementResponse>

    @GET("clothes/{id}")
    suspend fun getClothingDetail(
        @Header("Authorization") token: String,
        @Path("id") id: Int
    ): Response<VetementResponse>

    @PUT("clothes/{id}")
    suspend fun updateClothing(
        @Header("Authorization") token: String,
        @Path("id") id: Int,
        @Body request: VetementUpdateRequest
    ): Response<VetementResponse>

    @DELETE("clothes/{id}")
    suspend fun deleteClothing(
        @Header("Authorization") token: String,
        @Path("id") id: Int
    ): Response<Unit>

    // =================== IA (CLASSIFICATION) ===================
    @Multipart
    @POST("ai/classify")
    suspend fun classifyClothing(
        @Header("Authorization") token: String,
        @Part file: MultipartBody.Part
    ): Response<ClassifyResponse>

    @DELETE("ai/temp-upload")
    suspend fun deleteTempUpload(
        @Header("Authorization") token: String,
        @Query("image_url") imageUrl: String
    ): Response<Map<String, Any>>

    // =================== PLANNING ===================
    @GET("routines")
    suspend fun getRoutines(@Header("Authorization") token: String): Response<List<RoutineHebdomadaireResponse>>

    @POST("routines")
    suspend fun createRoutine(
        @Header("Authorization") token: String,
        @Body request: RoutineHebdomadaireRequest
    ): Response<RoutineHebdomadaireResponse>

    @PUT("routines/{id}")
    suspend fun updateRoutine(
        @Header("Authorization") token: String,
        @Path("id") id: Int,
        @Body request: RoutineHebdomadaireRequest
    ): Response<RoutineHebdomadaireResponse>

    @DELETE("routines/{id}")
    suspend fun deleteRoutine(
        @Header("Authorization") token: String,
        @Path("id") id: Int
    ): Response<Unit>

    @GET("events")
    suspend fun getEvents(@Header("Authorization") token: String): Response<List<EvenementResponse>>

    @POST("events")
    suspend fun createEvent(
        @Header("Authorization") token: String,
        @Body request: EvenementRequest
    ): Response<EvenementResponse>

    @DELETE("events/{id}")
    suspend fun deleteEvent(
        @Header("Authorization") token: String,
        @Path("id") id: Int
    ): Response<Unit>

    // =================== RECOMMANDATIONS ===================
    @POST("recommendations")
    suspend fun getRecommendation(
        @Header("Authorization") token: String,
        @Body request: RecommendationRequest = RecommendationRequest()
    ): Response<RecommendationResponse>

    // =================== TENUES / FAVORIS ===================
    @POST("outfits")
    suspend fun createOutfit(
        @Header("Authorization") token: String,
        @Body request: TenueCreateRequest
    ): Response<TenueResponse>

    @GET("outfits")
    suspend fun getOutfits(
        @Header("Authorization") token: String,
        @Query("favoris_only") favorisOnly: Boolean = false
    ): Response<List<TenueResponse>>

    @GET("outfits/{id}")
    suspend fun getOutfitDetail(
        @Header("Authorization") token: String,
        @Path("id") id: Int
    ): Response<TenueResponse>

    @PUT("outfits/{id}")
    suspend fun updateOutfit(
        @Header("Authorization") token: String,
        @Path("id") id: Int,
        @Query("estFavorite") estFavorite: Boolean? = null,
        @Query("marquee_portee") marqueePortee: Boolean? = null,
        @Query("occasion") occasion: String? = null
    ): Response<TenueResponse>

    @DELETE("outfits/{id}")
    suspend fun deleteOutfit(
        @Header("Authorization") token: String,
        @Path("id") id: Int
    ): Response<Unit>

    @DELETE("outfits/{id}/items/{vetement_id}")
    suspend fun removeItemFromOutfit(
        @Header("Authorization") token: String,
        @Path("id") outfitId: Int,
        @Path("vetement_id") itemId: Int
    ): Response<TenueResponse>

    @POST("outfits/{id}/items/{vetement_id}")
    suspend fun addItemToOutfit(
        @Header("Authorization") token: String,
        @Path("id") outfitId: Int,
        @Path("vetement_id") itemId: Int
    ): Response<TenueResponse>

    @POST("outfits/{id}/feedback")
    suspend fun submitFeedback(
        @Header("Authorization") token: String,
        @Path("id") outfitId: Int,
        @Body request: FeedbackRequest
    ): Response<FeedbackResponse>

    // =================== SHOPPING & AI SHOPPER ===================
    @GET("shopping/suggestions")
    suspend fun getShoppingSuggestions(
        @Header("Authorization") token: String,
        @Query("besoin") besoin: String? = null
    ): Response<List<ArticleCatalogueResponse>>

    @GET("shopping/catalogue")
    suspend fun getCatalogue(): Response<List<ArticleCatalogueResponse>>

    @POST("shopper/generate-outfits")
    suspend fun generateShopperOutfits(
        @Header("Authorization") token: String? = null,
        @Body request: ShopperPromptRequest
    ): Response<ShopperResultResponse>
}


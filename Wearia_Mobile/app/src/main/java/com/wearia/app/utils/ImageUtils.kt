package com.wearia.app.utils

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import android.util.Log
import java.io.File
import java.io.FileOutputStream
import kotlin.math.max

object ImageUtils {

    private const val TAG = "ImageUtils"

    /**
     * Optimise et compresse une image pour l'envoi vers le backend IA :
     * - Respecte l'orientation EXIF de l'appareil photo (évite les photos couchées).
     * - Sous-échantillonne lors de la lecture pour éviter les OutOfMemory (OOM).
     * - Redimensionne à une dimension maximale (1024px par défaut).
     * - Compresse en JPEG qualité 80% (taille réduite de ~10 Mo à ~150 Ko).
     * - Permet un upload quasi-instantané et élimine les erreurs de timeout réseau.
     */
    fun compressAndPrepareFile(
        context: Context,
        sourceFile: File,
        maxDim: Int = 1024,
        quality: Int = 80
    ): File {
        return try {
            if (!sourceFile.exists() || sourceFile.length() == 0L) {
                return sourceFile
            }

            // 1. Lire les dimensions originales sans charger les pixels en mémoire
            val boundsOptions = BitmapFactory.Options().apply {
                inJustDecodeBounds = true
            }
            BitmapFactory.decodeFile(sourceFile.absolutePath, boundsOptions)
            val origWidth = boundsOptions.outWidth
            val origHeight = boundsOptions.outHeight

            if (origWidth <= 0 || origHeight <= 0) {
                return sourceFile
            }

            // 2. Calculer inSampleSize
            var inSampleSize = 1
            val maxEdge = max(origWidth, origHeight)
            while ((maxEdge / (inSampleSize * 2)) >= maxDim) {
                inSampleSize *= 2
            }

            val decodeOptions = BitmapFactory.Options().apply {
                this.inSampleSize = inSampleSize
                inPreferredConfig = Bitmap.Config.RGB_565 // Économise 50% de mémoire RAM
            }

            val sampledBitmap = BitmapFactory.decodeFile(sourceFile.absolutePath, decodeOptions)
                ?: return sourceFile

            // 3. Corriger l'orientation EXIF si nécessaire
            val rotation = getExifRotation(sourceFile.absolutePath)
            val rotatedBitmap = if (rotation != 0f) {
                val matrix = Matrix().apply { postRotate(rotation) }
                val rotated = Bitmap.createBitmap(
                    sampledBitmap, 0, 0,
                    sampledBitmap.width, sampledBitmap.height,
                    matrix, true
                )
                if (rotated != sampledBitmap) {
                    sampledBitmap.recycle()
                }
                rotated
            } else {
                sampledBitmap
            }

            // 4. Redimensionner si les dimensions dépassent encore maxDim
            val finalBitmap = if (rotatedBitmap.width > maxDim || rotatedBitmap.height > maxDim) {
                val ratio = minOf(
                    maxDim.toFloat() / rotatedBitmap.width,
                    maxDim.toFloat() / rotatedBitmap.height
                )
                val targetW = max(1, (rotatedBitmap.width * ratio).toInt())
                val targetH = max(1, (rotatedBitmap.height * ratio).toInt())
                val scaled = Bitmap.createScaledBitmap(rotatedBitmap, targetW, targetH, true)
                if (scaled != rotatedBitmap) {
                    rotatedBitmap.recycle()
                }
                scaled
            } else {
                rotatedBitmap
            }

            // 5. Enregistrer le fichier compressé dans le cache
            val compressedFile = File(
                context.cacheDir,
                "wearia_compressed_${System.currentTimeMillis()}.jpg"
            )

            FileOutputStream(compressedFile).use { out ->
                finalBitmap.compress(Bitmap.CompressFormat.JPEG, quality, out)
            }

            finalBitmap.recycle()

            Log.d(TAG, "Image compressée avec succès : ${sourceFile.length() / 1024} Ko -> ${compressedFile.length() / 1024} Ko")
            compressedFile
        } catch (e: Exception) {
            Log.e(TAG, "Erreur lors de la compression de l'image, utilisation du fichier original : ${e.localizedMessage}")
            sourceFile
        }
    }

    private fun getExifRotation(path: String): Float {
        return try {
            val exif = ExifInterface(path)
            when (exif.getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)) {
                ExifInterface.ORIENTATION_ROTATE_90 -> 90f
                ExifInterface.ORIENTATION_ROTATE_180 -> 180f
                ExifInterface.ORIENTATION_ROTATE_270 -> 270f
                else -> 0f
            }
        } catch (e: Exception) {
            0f
        }
    }
}


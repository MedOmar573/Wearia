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
     * Supprime les fichiers temporaires de capture photo / galerie / compression
     * afin que la photo testée précédente soit nettoyée avant une nouvelle prise.
     */
    fun clearTemporaryCaptureFiles(context: Context, keepFile: File? = null) {
        try {
            val keepPath = keepFile?.canonicalPath
            context.cacheDir.listFiles()?.forEach { file ->
                if (!file.isFile) return@forEach
                val name = file.name.lowercase()
                val isTempCapture = name.startsWith("wearia_") || name.startsWith("picked_cloth_")
                if (isTempCapture && file.canonicalPath != keepPath) {
                    file.delete()
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "Nettoyage des fichiers temporaires incomplet : ${e.localizedMessage}")
        }
    }

    /**
     * Optimise et compresse une image pour l'envoi vers le backend IA :
     * - Respecte toutes les orientations EXIF (rotations et retournements).
     * - Décode en ARGB_8888 (24-bit RGB complet) pour éviter la dérive colorimétrique de RGB_565.
     * - Redimensionne en conservant strictement les proportions (maxDim = 1024px).
     * - Compresse en JPEG qualité 88% pour préserver fidèlement les couleurs et textures de tissu.
     */
    fun compressAndPrepareFile(
        context: Context,
        sourceFile: File,
        maxDim: Int = 1024,
        quality: Int = 88
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
                inPreferredConfig = Bitmap.Config.ARGB_8888
            }

            val sampledBitmap = BitmapFactory.decodeFile(sourceFile.absolutePath, decodeOptions)
                ?: return sourceFile

            // 3. Corriger l'orientation EXIF si nécessaire (rotations + symétries)
            val exifMatrix = getExifMatrix(sourceFile.absolutePath)
            val rotatedBitmap = if (!exifMatrix.isIdentity) {
                val rotated = Bitmap.createBitmap(
                    sampledBitmap, 0, 0,
                    sampledBitmap.width, sampledBitmap.height,
                    exifMatrix, true
                )
                if (rotated != sampledBitmap) {
                    sampledBitmap.recycle()
                }
                rotated
            } else {
                sampledBitmap
            }

            // 4. Redimensionner en conservant les proportions si les dimensions dépassent encore maxDim
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

            Log.d(
                TAG,
                "Image préparée (ARGB_8888, q=$quality) : ${sourceFile.length() / 1024} Ko -> ${compressedFile.length() / 1024} Ko"
            )
            compressedFile
        } catch (e: Exception) {
            Log.e(TAG, "Erreur lors de la compression de l'image, utilisation du fichier original : ${e.localizedMessage}")
            sourceFile
        }
    }

    private fun getExifMatrix(path: String): Matrix {
        val matrix = Matrix()
        return try {
            val exif = ExifInterface(path)
            when (exif.getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)) {
                ExifInterface.ORIENTATION_ROTATE_90 -> matrix.postRotate(90f)
                ExifInterface.ORIENTATION_ROTATE_180 -> matrix.postRotate(180f)
                ExifInterface.ORIENTATION_ROTATE_270 -> matrix.postRotate(270f)
                ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> matrix.postScale(-1f, 1f)
                ExifInterface.ORIENTATION_FLIP_VERTICAL -> matrix.postScale(1f, -1f)
                ExifInterface.ORIENTATION_TRANSPOSE -> {
                    matrix.postRotate(90f)
                    matrix.postScale(-1f, 1f)
                }
                ExifInterface.ORIENTATION_TRANSVERSE -> {
                    matrix.postRotate(270f)
                    matrix.postScale(-1f, 1f)
                }
            }
            matrix
        } catch (e: Exception) {
            matrix
        }
    }
}

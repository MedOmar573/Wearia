package com.wearia.app.ui.camera

import android.Manifest
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import com.wearia.app.R
import com.wearia.app.databinding.FragmentCameraBinding
import com.wearia.app.utils.ImageUtils
import com.wearia.app.utils.Resource
import com.wearia.app.viewmodel.ClothingViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.text.SimpleDateFormat
import java.util.*
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * CameraFragment : Capture de photo d'un vêtement via CameraX et import galerie.
 */
class CameraFragment : Fragment() {

    private var _binding: FragmentCameraBinding? = null
    private val binding get() = _binding!!

    private val viewModel: ClothingViewModel by activityViewModels { ClothingViewModel.Factory() }

    private var imageCapture: ImageCapture? = null
    private var cameraExecutor: ExecutorService? = null
    private lateinit var outputDir: File

    private val requestPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) {
                startCamera()
            } else {
                Toast.makeText(requireContext(), "Permission caméra refusée. Vous pouvez utiliser la galerie.", Toast.LENGTH_LONG).show()
            }
        }

    // Sélecteur d'image depuis la galerie
    private val galleryLauncher =
        registerForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
            uri?.let { handleGalleryImage(it) }
        }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentCameraBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        cameraExecutor = Executors.newSingleThreadExecutor()
        outputDir = requireContext().cacheDir

        // Vérification de la permission caméra
        if (ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        } else {
            requestPermissionLauncher.launch(Manifest.permission.CAMERA)
        }

        binding.btnCapture.setOnClickListener { takePhoto() }
        binding.btnGallery.setOnClickListener {
            try {
                galleryLauncher.launch("image/*")
            } catch (e: Exception) {
                Toast.makeText(requireContext(), "Erreur galerie : ${e.localizedMessage}", Toast.LENGTH_SHORT).show()
            }
        }

        viewModel.classifyState.observe(viewLifecycleOwner) { state ->
            if (state == null) return@observe
            when (state) {
                is Resource.Loading -> {
                    binding.btnCapture.isEnabled = false
                    binding.tvClassifyStatus.text = "Analyse IA en cours..."
                    binding.progressBar.visibility = View.VISIBLE
                }
                is Resource.Success -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnCapture.isEnabled = true
                    val result = state.data
                    binding.tvClassifyStatus.text = "Catégorie : ${result.category.uppercase()} " +
                            "· Couleur : ${result.color.uppercase()} " +
                            "· Confiance : ${(result.confidence * 100).toInt()}%"

                    // Naviguer uniquement si nous sommes encore sur CameraFragment
                    if (findNavController().currentDestination?.id == R.id.cameraFragment) {
                        val bundle = Bundle().apply {
                            putString("imageUrl", result.imageUrl)
                            putString("category", result.category)
                            putString("color", result.color)
                            putString("colorHex", result.colorHex)
                            putInt("suggestedTypeId", result.suggestedTypeId ?: -1)
                            putInt("suggestedColorId", result.suggestedColorId ?: -1)
                            putString("name", result.name)
                            putString("matiere", result.matiere)
                            putString("coupe", result.coupe)
                            putString("saison", result.saison)
                            putBoolean("estThermique", result.estThermique ?: false)
                            putBoolean("estImpermeable", result.estImpermeable ?: false)
                            putInt("styleId", result.styleId ?: 1)
                            putString("styleName", result.styleName)
                        }
                        viewModel.resetClassifyState()
                        findNavController().navigate(R.id.action_camera_to_addClothing, bundle)
                    }
                }
                is Resource.Error -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnCapture.isEnabled = true
                    binding.tvClassifyStatus.text = "Erreur : ${state.message}"
                    Toast.makeText(requireContext(), state.message, Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun startCamera() {
        val currentContext = context ?: return
        try {
            val cameraProviderFuture = ProcessCameraProvider.getInstance(currentContext)
            cameraProviderFuture.addListener({
                try {
                    if (_binding == null) return@addListener
                    val cameraProvider = cameraProviderFuture.get()
                    val preview = Preview.Builder().build().also {
                        it.setSurfaceProvider(binding.cameraPreview.surfaceProvider)
                    }
                    imageCapture = ImageCapture.Builder()
                        .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                        .build()

                    cameraProvider.unbindAll()

                    val cameraSelector = when {
                        cameraProvider.hasCamera(CameraSelector.DEFAULT_BACK_CAMERA) -> CameraSelector.DEFAULT_BACK_CAMERA
                        cameraProvider.hasCamera(CameraSelector.DEFAULT_FRONT_CAMERA) -> CameraSelector.DEFAULT_FRONT_CAMERA
                        else -> null
                    }

                    if (cameraSelector != null) {
                        cameraProvider.bindToLifecycle(
                            viewLifecycleOwner,
                            cameraSelector,
                            preview,
                            imageCapture
                        )
                    } else {
                        Toast.makeText(currentContext, "Caméra non détectée. Vous pouvez utiliser le bouton galerie.", Toast.LENGTH_LONG).show()
                    }
                } catch (t: Throwable) {
                    Toast.makeText(currentContext, "CameraX indisponible sur cet appareil. Utilisez la galerie.", Toast.LENGTH_SHORT).show()
                }
            }, ContextCompat.getMainExecutor(currentContext))
        } catch (t: Throwable) {
            Toast.makeText(currentContext, "Erreur initialisation caméra : ${t.localizedMessage}", Toast.LENGTH_SHORT).show()
        }
    }

    private fun takePhoto() {
        val capture = imageCapture ?: run {
            Toast.makeText(requireContext(), "Caméra non prête. Utilisez le bouton Galerie.", Toast.LENGTH_SHORT).show()
            return
        }
        val photoFile = File(
            outputDir,
            "wearia_${SimpleDateFormat("yyyyMMdd_HHmmss", Locale.FRANCE).format(Date())}.jpg"
        )
        val outputOptions = ImageCapture.OutputFileOptions.Builder(photoFile).build()

        binding.btnCapture.isEnabled = false
        binding.progressBar.visibility = View.VISIBLE
        binding.tvClassifyStatus.text = "Capture en cours..."

        capture.takePicture(
            outputOptions,
            ContextCompat.getMainExecutor(requireContext()),
            object : ImageCapture.OnImageSavedCallback {
                override fun onError(e: ImageCaptureException) {
                    binding.btnCapture.isEnabled = true
                    binding.progressBar.visibility = View.GONE
                    binding.tvClassifyStatus.text = "Erreur capture : ${e.message}"
                    Toast.makeText(requireContext(), "Erreur capture : ${e.message}", Toast.LENGTH_SHORT).show()
                }

                override fun onImageSaved(output: ImageCapture.OutputFileResults) {
                    val ctx = context ?: return
                    binding.tvClassifyStatus.text = "Optimisation de l'image..."
                    lifecycleScope.launch(Dispatchers.IO) {
                        val optimizedFile = ImageUtils.compressAndPrepareFile(ctx, photoFile)
                        withContext(Dispatchers.Main) {
                            binding.tvClassifyStatus.text = "Analyse IA (KNN + OpenCV)..."
                            viewModel.classifyImage(optimizedFile)
                        }
                    }
                }
            }
        )
    }

    private fun handleGalleryImage(uri: Uri) {
        val ctx = context ?: return
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val inputStream = ctx.contentResolver.openInputStream(uri) ?: run {
                    withContext(Dispatchers.Main) {
                        Toast.makeText(ctx, "Impossible de lire l'image sélectionnée.", Toast.LENGTH_SHORT).show()
                    }
                    return@launch
                }
                val rawTempFile = File(outputDir, "wearia_gallery_${System.currentTimeMillis()}.jpg")
                rawTempFile.outputStream().use { output ->
                    inputStream.copyTo(output)
                }
                val optimizedFile = ImageUtils.compressAndPrepareFile(ctx, rawTempFile)
                withContext(Dispatchers.Main) {
                    Toast.makeText(ctx, "Image importée, analyse IA en cours...", Toast.LENGTH_SHORT).show()
                    viewModel.classifyImage(optimizedFile)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(ctx, "Erreur import : ${e.localizedMessage}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        try {
            cameraExecutor?.shutdown()
        } catch (e: Exception) {
            // ignore
        }
        _binding = null
    }
}

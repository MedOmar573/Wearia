package com.wearia.app.utils

import android.animation.AnimatorSet
import android.animation.ObjectAnimator
import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Color
import android.view.HapticFeedbackConstants
import android.view.MotionEvent
import android.view.View
import android.view.animation.DecelerateInterpolator
import android.view.animation.OvershootInterpolator
import android.widget.TextView
import androidx.core.content.ContextCompat
import com.wearia.app.R

/**
 * Extensions d'interactivité et de retour visuel pour la direction "Fresh Fashion Tech".
 * Gère l'effet de pression (scale 0.96f), l'haptique légère et les badges pastels de catégories.
 */

@SuppressLint("ClickableViewAccessibility")
fun View.addPressEffect(scaleFactor: Float = 0.96f) {
    setOnTouchListener { v, event ->
        when (event.action) {
            MotionEvent.ACTION_DOWN -> {
                v.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
                v.animate()
                    .scaleX(scaleFactor)
                    .scaleY(scaleFactor)
                    .setDuration(100)
                    .setInterpolator(DecelerateInterpolator())
                    .start()
            }
            MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                v.animate()
                    .scaleX(1.0f)
                    .scaleY(1.0f)
                    .setDuration(150)
                    .setInterpolator(OvershootInterpolator(1.2f))
                    .start()
            }
        }
        false
    }
}

/**
 * Configure un clic avec retour tactile (scale + vibration) et exécution sécurisée de l'action.
 */
@SuppressLint("ClickableViewAccessibility")
fun View.setOnBounceClickListener(onClickListener: (View) -> Unit) {
    setOnTouchListener { v, event ->
        when (event.action) {
            MotionEvent.ACTION_DOWN -> {
                v.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
                v.animate()
                    .scaleX(0.96f)
                    .scaleY(0.96f)
                    .setDuration(90)
                    .setInterpolator(DecelerateInterpolator())
                    .start()
            }
            MotionEvent.ACTION_UP -> {
                v.animate()
                    .scaleX(1.0f)
                    .scaleY(1.0f)
                    .setDuration(130)
                    .setInterpolator(OvershootInterpolator(1.2f))
                    .start()
                v.performClick()
                onClickListener(v)
            }
            MotionEvent.ACTION_CANCEL -> {
                v.animate()
                    .scaleX(1.0f)
                    .scaleY(1.0f)
                    .setDuration(120)
                    .start()
            }
        }
        true
    }
}

/**
 * Animation d'apparition avec fade et translation vers le haut
 */
fun View.fadeInUp(duration: Long = 350, startDelay: Long = 0) {
    alpha = 0f
    translationY = 40f
    visibility = View.VISIBLE
    animate()
        .alpha(1f)
        .translationY(0f)
        .setDuration(duration)
        .setStartDelay(startDelay)
        .setInterpolator(DecelerateInterpolator())
        .start()
}

/**
 * Applique le badge pastel officiel "Fresh Fashion Tech" selon la catégorie du vêtement.
 */
fun TextView.applyCategoryBadge(category: String?) {
    val norm = category?.trim()?.lowercase() ?: ""
    when {
        norm.contains("haut") || norm.contains("top") || norm.contains("t-shirt") || norm.contains("chemise") -> {
            setBackgroundResource(R.drawable.bg_badge_haut)
            setTextColor(ContextCompat.getColor(context, R.color.badge_haut_text))
        }
        norm.contains("bas") || norm.contains("pantalon") || norm.contains("jean") || norm.contains("jupe") || norm.contains("short") -> {
            setBackgroundResource(R.drawable.bg_badge_bas)
            setTextColor(ContextCompat.getColor(context, R.color.badge_bas_text))
        }
        norm.contains("chauss") || norm.contains("basket") || norm.contains("sneaker") || norm.contains("botte") -> {
            setBackgroundResource(R.drawable.bg_badge_chaussures)
            setTextColor(ContextCompat.getColor(context, R.color.badge_chaussures_text))
        }
        norm.contains("veste") || norm.contains("manteau") || norm.contains("blouson") || norm.contains("cardigan") -> {
            setBackgroundResource(R.drawable.bg_badge_veste)
            setTextColor(ContextCompat.getColor(context, R.color.badge_veste_text))
        }
        norm.contains("robe") -> {
            setBackgroundResource(R.drawable.bg_badge_robe)
            setTextColor(ContextCompat.getColor(context, R.color.badge_robe_text))
        }
        norm.contains("accessoire") || norm.contains("chapeau") || norm.contains("écharpe") || norm.contains("sac") -> {
            setBackgroundResource(R.drawable.bg_badge_accessoire)
            setTextColor(ContextCompat.getColor(context, R.color.badge_accessoire_text))
        }
        else -> {
            setBackgroundResource(R.drawable.bg_badge_haut)
            setTextColor(ContextCompat.getColor(context, R.color.badge_haut_text))
        }
    }
}

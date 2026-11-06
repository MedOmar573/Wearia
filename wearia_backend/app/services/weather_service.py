import logging
import requests
from typing import Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class WeatherService:
    @staticmethod
    def get_weather_for_city(city: str = "Tunis") -> Dict[str, Any]:
        """
        Récupère la météo actuelle pour une ville via OpenWeatherMap.
        Si la clé API est absente ou si une erreur survient, renvoie une météo par défaut réaliste.
        """
        api_key = settings.OPENWEATHERMAP_API_KEY
        if not api_key:
            return {
                "temperature": 20.0,
                "precipitations": False,
                "description": "Ensoleillé (défaut)",
                "city": city
            }

        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": api_key,
            "units": "metric",
            "lang": "fr"
        }

        try:
            response = requests.get(url, params=params, timeout=4)
            if response.status_code == 200:
                data = response.json()
                temp = data.get("main", {}).get("temp", 20.0)
                weather_list = data.get("weather", [])
                desc = weather_list[0].get("description", "Dégagé") if weather_list else "Dégagé"
                main_weather = weather_list[0].get("main", "").lower() if weather_list else ""
                
                # Précipitations si pluie, neige, bruine ou orage
                has_rain = any(keyword in main_weather for keyword in ["rain", "drizzle", "snow", "thunderstorm"])

                return {
                    "temperature": float(temp),
                    "precipitations": has_rain,
                    "description": desc.capitalize(),
                    "city": city
                }
            else:
                logger.warning(f"Erreur OpenWeatherMap ({response.status_code}): {response.text}")
        except Exception as e:
            logger.error(f"Exception lors de la récupération météo : {e}")

        # Valeur de repli sécurisée en cas d'échec
        return {
            "temperature": 18.0,
            "precipitations": False,
            "description": "Météo tempérée (secours)",
            "city": city
        }


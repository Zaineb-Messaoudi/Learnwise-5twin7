"""Generation d'illustrations : Hugging Face d'abord, Pollinations (gratuit, sans cle),
diffusers local (Stable Diffusion), Gemini en secours, puis fallback local Pillow.

Les fournisseurs essayes (et leur ordre) se reglent dans .env :
    IMAGE_PROVIDERS=huggingface,pollinations,diffusers,gemini
"""
import io
import logging

from PIL import Image, ImageDraw, ImageFont

from .config import get_setting
from .errors import AIServiceError
from .hf_common import hf_error

logger = logging.getLogger(__name__)


def _huggingface_image(prompt):
    token = get_setting('HF_API_TOKEN')
    if not token:
        raise AIServiceError(
            'hf_not_configured', "Token HF_API_TOKEN manquant dans le fichier .env."
        )
    try:
        from huggingface_hub import InferenceClient
    except ImportError as exc:
        raise AIServiceError(
            'hf_sdk_missing', "Paquet manquant : pip install huggingface_hub"
        ) from exc

    try:
        client = InferenceClient(token=token)
        image = client.text_to_image(
            prompt,
            model=get_setting('HF_IMAGE_MODEL', 'black-forest-labs/FLUX.1-schnell'),
        )
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        return buffer.getvalue()
    except Exception as exc:
        raise hf_error(
            exc,
            'illustration_error',
            "La generation d'image a echoue. Reessaie dans un instant.",
        ) from exc


def _pollinations_image(prompt):
    """Generation d'image gratuite via Pollinations.ai (aucune cle API requise)."""
    try:
        import requests
    except ImportError as exc:
        raise AIServiceError(
            'pollinations_sdk_missing', "Paquet manquant : pip install requests"
        ) from exc

    try:
        import urllib.parse
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=768&nologo=true"
        response = requests.get(url, timeout=60)
        if response.status_code != 200:
            raise AIServiceError(
                'pollinations_error',
                f"Pollinations a retourne le statut {response.status_code}.",
                retryable=True,
            )
        return response.content
    except AIServiceError:
        raise
    except Exception as exc:
        raise AIServiceError(
            'pollinations_error',
            f"La generation d'image via Pollinations a echoue : {exc}",
            retryable=True,
        ) from exc


def _diffusers_image(prompt):
    """Generation d'image locale via diffusers + Stable Diffusion (aucun appel externe)."""
    try:
        import torch
        from diffusers import StableDiffusionPipeline
    except ImportError as exc:
        raise AIServiceError(
            'diffusers_sdk_missing',
            "Paquets manquants : pip install diffusers transformers accelerate safetensors torch",
        ) from exc

    model_id = get_setting('DIFFUSERS_MODEL', 'stabilityai/stable-diffusion-2-1-base')
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    try:
        pipe = StableDiffusionPipeline.from_pretrained(
            model_id,
            torch_dtype=dtype,
            use_safetensors=True,
        )
        pipe = pipe.to(device)

        image = pipe(
            prompt,
            num_inference_steps=20,
            guidance_scale=7.5,
        ).images[0]

        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        return buffer.getvalue()
    except Exception as exc:
        raise AIServiceError(
            'diffusers_error',
            f"La generation d'image locale (diffusers) a echoue : {exc}",
            retryable=False,
        ) from exc


def _gemini_image(prompt):
    api_key = get_setting('GEMINI_API_KEY')
    if not api_key:
        raise AIServiceError(
            'gemini_not_configured',
            "Cle GEMINI_API_KEY manquante dans le fichier .env.",
        )
    try:
        from google import genai
        from google.genai import types
        from PIL import Image
    except ImportError as exc:
        raise AIServiceError(
            'gemini_sdk_missing', "Paquet manquant : pip install google-genai pillow"
        ) from exc

    model = get_setting('GEMINI_IMAGE_MODEL', 'gemini-2.5-flash-image')
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=['IMAGE']),
        )
    except Exception as exc:
        code = getattr(exc, 'code', None)
        if code == 404:
            raise AIServiceError(
                'gemini_image_model_not_found',
                "Modele d'image Gemini indisponible : verifie GEMINI_IMAGE_MODEL "
                "dans .env.",
            ) from exc
        if code == 429:
            raise AIServiceError(
                'gemini_image_quota',
                "Quota d'images Gemini atteint pour le moment.",
                retryable=True,
            ) from exc
        raise AIServiceError(
            'illustration_error',
            "La generation d'image a echoue. Reessaie dans un instant.",
            retryable=True,
        ) from exc

    for candidate in response.candidates or []:
        content = getattr(candidate, 'content', None)
        for part in (getattr(content, 'parts', None) or []):
            inline = getattr(part, 'inline_data', None)
            if inline is not None and inline.data:
                buffer = io.BytesIO()
                Image.open(io.BytesIO(inline.data)).save(buffer, format='PNG')
                return buffer.getvalue()
    raise AIServiceError('illustration_empty', "Gemini n'a renvoye aucune image.")


def _local_pillow_image(prompt):
    """Genere un diagramme pedagogique simple avec Pillow quand les IA externes sont indisponibles."""
    width, height = 800, 600
    img = Image.new('RGB', (width, height), color='#f8fafc')
    draw = ImageDraw.Draw(img)

    # Couleurs
    primary = '#2563eb'
    secondary = '#10b981'
    accent = '#f5e00b'
    text_color = '#1e293b'

    try:
        title_font = ImageFont.truetype('arial.ttf', 32)
        body_font = ImageFont.truetype('arial.ttf', 24)
        small_font = ImageFont.truetype('arial.ttf', 18)
    except Exception:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Titre
    title = "Illustration pedagogique"
    draw.text((40, 30), title, fill=primary, font=title_font)

    # Ligne decorative
    draw.line([(40, 80), (width - 40, 80)], fill=primary, width=3)

    # Boite centrale
    draw.rounded_rectangle([(80, 120), (width - 80, 480)], fill='white', outline=primary, width=3, radius=20)

    # Texte dans la boite
    draw.text((120, 160), "Diagramme genere localement", fill=primary, font=body_font)
    draw.text((120, 210), "Prompt :", fill=text_color, font=small_font)

    # Wrapper le texte du prompt sur plusieurs lignes
    words = prompt.split()
    lines = []
    current = ""
    for word in words:
        test = current + (" " if current else "") + word
        if len(test) > 55:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    y = 250
    for line in lines[:6]:
        draw.text((120, y), line, fill=text_color, font=small_font)
        y += 40

    # Pied de page
    draw.text((40, height - 50), "Learnwise - Illustration generee sans appel IA externe (quota epuise)",
              fill='#64748b', font=small_font)

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


PROVIDERS = {
    'huggingface': _huggingface_image,
    'pollinations': _pollinations_image,
    'diffusers': _diffusers_image,
    'gemini': _gemini_image,
}


def generate_image(prompt):
    """Retourne les octets d'une image PNG, en essayant chaque fournisseur, puis un fallback local Pillow."""
    names = get_setting('IMAGE_PROVIDERS', 'huggingface,pollinations,diffusers,gemini').split(',')
    last_error = None
    for name in (n.strip() for n in names):
        provider = PROVIDERS.get(name)
        if provider is None:
            continue
        try:
            return provider(prompt)
        except AIServiceError as exc:
            last_error = exc
            logger.warning("Illustration : fournisseur %s indisponible (%s)", name, exc.code)
    # Fallback local : generer un diagramme avec Pillow (aucun appel externe, toujours disponible)
    logger.warning("Illustration : tous les fournisseurs IA indisponibles, utilisation du fallback local Pillow")
    try:
        return _local_pillow_image(prompt)
    except Exception as exc:
        raise last_error or AIServiceError(
            'illustration_not_configured',
            "Aucun fournisseur d'images configure et le fallback local a echoue.",
        ) from exc

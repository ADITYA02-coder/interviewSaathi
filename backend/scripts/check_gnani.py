"""Run this FIRST once you have your Gnani key:   python -m scripts.check_gnani
For each language it synthesises a sentence with Timbre, feeds that audio back into Prisma, and prints a table,
so you only promise the languages that really work in your demo."""
import asyncio
import time
from app import gnani

SENTENCES = {
    "en-IN": "Explain the difference between an interface and an abstract class in Java.",
    "hi-IN": "जावा में इंटरफ़ेस और एब्सट्रैक्ट क्लास के बीच अंतर समझाइए।",
    "hinglish": "Java mein interface aur abstract class ka difference explain kijiye.",
    "ta-IN": "ஜாவாவில் இன்டர்ஃபேஸ் மற்றும் அப்ஸ்ட்ராக்ட் கிளாஸ் இடையே உள்ள வேறுபாட்டை விளக்குங்கள்.",
    "te-IN": "జావాలో ఇంటర్‌ఫేస్ మరియు అబ్‌స్ట్రాక్ట్ క్లాస్ మధ్య తేడా వివరించండి.",
    "kn-IN": "ಜಾವಾದಲ್ಲಿ ಇಂಟರ್ಫೇಸ್ ಮತ್ತು ಅಬ್ಸ್ಟ್ರ್ಯಾಕ್ಟ್ ಕ್ಲಾಸ್ ನಡುವಿನ ವ್ಯತ್ಯಾಸ ವಿವರಿಸಿ.",
    "ml-IN": "ജാവയിലെ ഇന്റർഫേസും അബ്സ്ട്രാക്റ്റ് ക്ലാസും തമ്മിലുള്ള വ്യത്യാസം വിശദീകരിക്കുക.",
    "mr-IN": "जावामधील इंटरफेस आणि अ‍ॅबस्ट्रॅक्ट क्लास यांच्यातील फरक सांगा.",
    "bn-IN": "জাভায় ইন্টারফেস এবং অ্যাবস্ট্রাক্ট ক্লাসের মধ্যে পার্থক্য ব্যাখ্যা করুন।",
    "gu-IN": "જાવામાં ઇન્ટરફેસ અને એબ્સ્ટ્રેક્ટ ક્લાસ વચ્ચેનો તફાવત સમજાવો.",
    "pa-IN": "ਜਾਵਾ ਵਿੱਚ ਇੰਟਰਫੇਸ ਅਤੇ ਐਬਸਟਰੈਕਟ ਕਲਾਸ ਵਿੱਚ ਅੰਤਰ ਸਮਝਾਓ।",
}


async def main():
    if not gnani.configured():
        raise SystemExit("Set GNANI_API_KEY in .env first.")
    print(f"{'language':10} {'voice':9} {'TTS':>8} {'STT':>8}  round-trip transcript")
    for lang, cfg in gnani.LANGUAGES.items():
        for gender, voice in cfg["voices"].items():
            if not voice:
                continue
            tts_l = cfg["tts"]
            try:
                t0 = time.perf_counter()
                mp3 = await gnani.synthesize(SENTENCES[lang], voice, tts_l)
                t_tts = (time.perf_counter() - t0) * 1000
            except Exception as e:
                print(f"{lang:10} {voice:9} TTS FAILED: {e}")
                continue
            try:  # Prisma accepts MP3 per Gnani's docs, so we can feed the synthesised audio straight back
                t0 = time.perf_counter()
                out = await gnani.transcribe(mp3, "check.mp3", "audio/mpeg", lang)
                t_stt = (time.perf_counter() - t0) * 1000
                print(f"{lang:10} {voice:9} {t_tts:7.0f}ms {t_stt:7.0f}ms  [{out['language_code']}] {out['transcript'][:70]}")
            except Exception as e:
                print(f"{lang:10} {voice:9} {t_tts:7.0f}ms   STT FAILED: {e}")


if __name__ == "__main__":
    asyncio.run(main())

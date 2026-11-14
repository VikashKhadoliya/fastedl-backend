import random
import re
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/creator", tags=["creator-tools"])

# ==========================================
# 1. CAPTION GENERATOR
# ==========================================

CAPTION_DATA: Dict[str, Dict[str, Dict[str, List[str]]]] = {
    "travel": {
        "en": {
            "short": [
                "Lost in the right direction. ✈️",
                "Passport full of stamps, heart full of memories.",
                "Wander often, wonder always. 🌍",
                "Chasing horizons and timeless sunsets.",
                "Catch flights, not feelings.",
                "Another pin on the map. 📍",
                "Finding paradise wherever I go.",
                "Collect moments, not things."
            ],
            "medium": [
                "There is a whole world out there waiting to be explored. Taking the scenic route every single time. ✨✈️",
                "Somewhere between departure gates and mountain peaks, I found my peace. Where should the compass point next? 🧭",
                "Not all classrooms have four walls. Some of the greatest lessons come with muddy boots and passport stamps. 🎒🌏",
                "Salt in the air, sand in my hair, and endless views on the horizon. Never leaving this place. 🌊☀️"
            ],
            "long": [
                "They say traveling leaves you speechless, then turns you into a storyteller. Walking down cobblestone alleys in a city where every corner has centuries of history reminds me how vast and beautiful our world really is. Keep wandering, keep learning, and never stop seeking new perspectives. What destination is on your bucket list this year? Drop it below! 👇✈️"
            ]
        },
        "hi": {
            "short": [
                "सफ़र खूबसूरत है मंज़िल से भी। ✈️✨",
                "यादें बनाओ, बहाने नहीं। 🌍",
                "नई राहें, नए नज़ारे। 🎒",
                "हवाओं के रुख पर दिल चल पड़ा। 🌄",
                "मुसाफ़िर हैं हम, कारवां साथ है। 🧭"
            ],
            "medium": [
                "जब दिल घूमने को कहे, तो बैग पैक कर लेना चाहिए। ज़िन्दगी जीने का असली मज़ा नई जगहों को देखने में ही है। 🏞️✨",
                "रास्तों की धूल भी खुशबू बन जाती है जब सफ़र अपने सपनों की तरफ हो। अगला स्टॉप कहाँ होना चाहिए? कमेंट्स में बताएं! 📍🌏"
            ],
            "long": [
                "सफ़र केवल एक जगह से दूसरी जगह जाना नहीं, बल्कि खुद को नए सिरे से ढूंढना है। पहाड़ों की ताज़ी हवा और अनजान गलियों की सुकून भरी शामें हमेशा दिल में बस जाती हैं। ज़िन्दगी छोटी है और दुनिया बहुत बड़ी—घूमते रहिए, सीखते रहिए। आपका पसंदीदा हॉलिडे डेस्टिनेशन कौन सा है? 👇✈️"
            ]
        }
    },
    "fitness": {
        "en": {
            "short": [
                "Discipline over motivation. Every single day. 💪",
                "One more rep. One day closer.",
                "Sweat is just weakness leaving the body.",
                "Consistency beats talent every time. 🔥",
                "Build yourself from the ground up."
            ],
            "medium": [
                "Your only competition is the reflection in the mirror from yesterday. Put in the work when nobody is watching. 🏋️‍♂️💯",
                "Progress is not linear, but consistency is undefeated. Trust the process, respect the recovery, and show up. ⚡"
            ],
            "long": [
                "Transformation doesn't happen overnight in the gym. It is built across hundreds of quiet mornings, balanced meals, and choices to keep going when giving up would be easier. Focus on forming sustainable habits, celebrate the small personal records, and stay patient with yourself. What fitness goal are you attacking this month? Let's get it! 💪🔥"
            ]
        },
        "hi": {
            "short": [
                "मेहनत इतनी खामोशी से करो कि सफलता शोर मचा दे। 💪🔥",
                "पसीना आज बहाओगे, तभी चमक कल आएगी।",
                "खुद को हर रोज़ बेहतर बनाओ। ⚡",
                "बहाने छोड़ो, मेहनत चुनो। 🏋️‍♂️"
            ],
            "medium": [
                "शरीर तब बदलता है जब दिमाग हार मानने से मना कर दे। हर रोज़ की छोटी कोशिशें ही बड़ा बदलाव लाती हैं। 💯🔥",
                "सफलता प्लेट में रखकर नहीं मिलती, इसे जिम की हर एक रिपटीशन से कमाना पड़ता है। आज का वर्कआउट पूरा हुआ? 💪"
            ],
            "long": [
                "फिटनेस कोई एक दिन का लक्ष्य नहीं, बल्कि जीने का तरीका है। जब आप अपनी सेहत को प्राथमिकता देते हैं, तो आपका आत्मविश्वास खुद ब खुद बढ़ जाता है। कभी थक कर रुकें नहीं, बस आगे बढ़ते रहें। अपने लक्ष्य पर अडिग रहें और खुद पर भरोसा रखें! 🏋️‍♂️✨"
            ]
        }
    },
    "fashion": {
        "en": {
            "short": [
                "Style is a way to say who you are without speaking. ✨",
                "Life is too short to wear boring clothes.",
                "Elegance is an attitude. 🖤",
                "Dressed in confidence and good lighting.",
                "Simplicity is the keynote of all true elegance."
            ],
            "medium": [
                "Fashion fades, but authentic personal style is eternal. Mixing classic staples with modern silhouettes today. 🧥🕶️",
                "When your outfit matches your ambition, you are ready to conquer the room. Keep it sharp, keep it effortless. 💫"
            ],
            "long": [
                "True style isn't about chasing every fleeting micro-trend—it's about understanding what makes you feel powerful, comfortable, and undeniably yourself. Investing in quality timeless essentials allows your personality to shine through without saying a word. Rate this look from 1 to 10 in the comments below! 👇✨"
            ]
        },
        "hi": {
            "short": [
                "सादगी में ही असली खूबसूरती है। ✨",
                "अंदाज अपना, पहचान अपनी। 💫",
                "कपड़े नहीं, आत्मविश्वास पहनें। 🕶️",
                "सादगी और स्टाइल का सही मेल। 🖤"
            ],
            "medium": [
                "फ़ैशन वह है जो बाज़ार बेचता है, स्टाइल वह है जो आप खुद बनाते हैं। आज का लुक कैसा लगा? 👗✨",
                "जब आपका पहनावा आपके मिजाज से मेल खाए, तो हर दिन एक फ़ैशन शो बन जाता है। सादगी में स्टाइल! 🧥💫"
            ],
            "long": [
                "स्टाइल का मतलब महंगे ब्रांड्स नहीं, बल्कि यह है कि आप खुद को कैसे पेश करते हैं। जब आप आत्मविश्वास पहनते हैं, तो हर पोशाक खास लगने लगती है। अपने अंदाज को अपनी पहचान बनाएं। आपको यह स्टाइल कैसा लगा? नीचे कमेंट करें! 👇✨"
            ]
        }
    },
    "attitude": {
        "en": {
            "short": [
                "Silent moves, loud results. 👑",
                "I am not a second choice. Either pick me or watch me walk.",
                "Forgive, forget, and elevate. 🚀",
                "Confidence level: Selfie with no filter.",
                "Know your worth, then add tax."
            ],
            "medium": [
                "They will judge you anyway, so you might as well give them something unforgettable to look at. Moving forward in silence. 🦅⚡",
                "Don't study me, you won't graduate. Focus on building an empire while staying grounded in your roots. 💼🔥"
            ],
            "long": [
                "Your energy is your currency—stop spending it on people and spaces that don't value your growth. When you master the art of emotional control and stay locked onto your vision, distractions naturally fade away. Stay patient, stay hungry, and let your achievements do all the talking. 👑🔥"
            ]
        },
        "hi": {
            "short": [
                "खामोशी हमारी पहचान है, शोर कामयाबी मचाएगी। 👑",
                "हुनर होगा तो दुनिया खुद कदर करेगी। 🔥",
                "हम अपना मुकाम खुद बनाते हैं। 🚀",
                "अंदाज अलग है, इसलिए बात अलग है। ⚡"
            ],
            "medium": [
                "दुनिया क्या सोचेगी यह सोचना हमारा काम नहीं। हमारा काम तो बस अपने सपनों को हकीकत में बदलना है। 🦁🔥",
                "रास्ते मुश्किल हो सकते हैं लेकिन इरादे पत्थर जैसे मजबूत हैं। खुद पर यकीन रखो, मंजिल जरूर मिलेगी। 👑"
            ],
            "long": [
                "लोग अक्सर आपको आपकी मौजूदा स्थिति से आंकते हैं, लेकिन उन्हें नहीं पता कि आपके हौसले कितने बड़े हैं। खामोशी से अपनी मंज़िल की ओर बढ़ते रहिए, वक्त आने पर जवाब आपकी कामयाबी खुद दे देगी। अपना रास्ता खुद बनाओ और उस पर गर्व करो! 🦅🔥"
            ]
        }
    },
    "business": {
        "en": {
            "short": [
                "Dream big. Execute bigger. 📈",
                "Build in silence. Let success make the noise.",
                "Turn ambition into action. 💼",
                "Opportunity doesn't knock—you build the door.",
                "Scale solutions, not excuses."
            ],
            "medium": [
                "Entrepreneurship is about solving real problems for real people. Stay obsessed with the process and the profits will follow. 📊💡",
                "The distance between dreams and reality is called execution. Wake up with determination, go to bed with satisfaction. 🚀"
            ],
            "long": [
                "Building something meaningful takes patience that most people aren't willing to practice. Failures aren't dead ends—they are data points guiding your next pivot. Protect your focus, surround yourself with builders, and keep delivering undeniable value every single day. What project are you currently scaling? Let's connect! 💼📈"
            ]
        },
        "hi": {
            "short": [
                "सपनों को हकीकत में बदलने का समय आ गया है। 💼📈",
                "सोच बड़ी रखो, रास्ते अपने आप बन जाएंगे। 🚀",
                "मेहनत का कोई शॉर्टकट नहीं होता। 💡",
                "कामयाबी वही है जो संघर्ष के बाद मिले। 📊"
            ],
            "medium": [
                "व्यापार में वही आगे बढ़ता है जो जोखिम उठाने और नया सीखने से डरता नहीं। समस्या का समाधान बनो, सफलता कदम चूमेगी। 💼✨",
                "बड़ा सोचो, शुरुआत चाहे छोटी हो लेकिन इरादे बुलंद होने चाहिए। आज की मेहनत कल का भविष्य बनाएगी। 📈🔥"
            ],
            "long": [
                "सफलता किसी इत्तेफाक का नाम नहीं है, यह रोज़ाना की गई कड़ी मेहनत, सही फैसलों और कभी हार न मानने की आदत का परिणाम है। जब आप अपने काम को लगन और ईमानदारी से करते हैं, तो कोई भी रुकावट आपको रोक नहीं सकती। अपने लक्ष्यों पर अडिग रहें! 💼🚀"
            ]
        }
    },
    "lifestyle": {
        "en": {
            "short": [
                "Living gently, loving deeply. 🌿",
                "Slow mornings and peaceful evenings. ☕",
                "Creating a life I don't need a vacation from.",
                "Romanticizing the little everyday moments. ✨",
                "Grateful for right here, right now."
            ],
            "medium": [
                "A quiet mind, a warm cup of coffee, and sunlight streaming through the window. It's the simple things that fill the soul. ☀️☕",
                "Life isn't meant to be rushed through. Slow down, appreciate how far you've come, and breathe in the present. 🌸🍃"
            ],
            "long": [
                "Sometimes the greatest luxury is having a quiet evening to reset, reflect, and appreciate the small joys we so often overlook in the daily rush. Cultivate gratitude for where you are today while staying excited for tomorrow. How do you recharge your energy after a busy week? Share your favorite ritual! ☕🌿"
            ]
        },
        "hi": {
            "short": [
                "सुकून भरी ज़िंदगी, खुशियों का संसार। 🌿✨",
                "हर लम्हे को मुस्कुराकर जियो। ☕",
                "सादगी में ही सारा सुकून है। 🌸",
                "आज में जियो, कल की चिंता छोड़ो। 🍃"
            ],
            "medium": [
                "ज़िन्दगी उतनी ही खूबसूरत है जितना आप इसे देखना चाहते हैं। छोटी-छोटी बातों में खुशियाँ तलाशना ही असली कला है। ☕✨",
                "एक कप चाय, ठंडी हवा और सुकून के कुछ पल। कभी-कभी खुद के साथ वक्त बिताना सबसे अच्छा अहसास होता है। 🌸🌿"
            ],
            "long": [
                "भागदौड़ भरी इस दुनिया में सबसे मुश्किल और सबसे जरूरी है अपने लिए थोड़ा सुकून ढूंढना। जब आप वर्तमान में जीना सीख जाते हैं, तो हर दिन एक उपहार लगने लगता है। अपनों के साथ मुस्कुराइए और हर पल का आनंद लीजिए। 🌿☕✨"
            ]
        }
    },
    "love": {
        "en": {
            "short": [
                "You are my favorite notification. ❤️",
                "Found home in your laughter.",
                "Every love story is beautiful, but ours is my favorite. 🌹",
                "Together is my favorite place to be.",
                "With you, time stands still."
            ],
            "medium": [
                "In a room full of art, I would still look at you. Thank you for making ordinary days feel like poetry. 💌✨",
                "Love isn't finding someone you can live with—it's finding the one you simply cannot imagine life without. 🌹❤️"
            ],
            "long": [
                "The best kind of love is the one that awakens the soul, plants fire in our hearts, and brings peace to our minds. Walking beside you through every chapter of life makes the journey unforgettable. Tag your favorite person in the comments below! 👇❤️"
            ]
        },
        "hi": {
            "short": [
                "तुम साथ हो तो हर मौसम सुहाना है। ❤️✨",
                "तेरी मुस्कान ही मेरी खुशियों की वजह है। 🌹",
                "इश्क़ वो नहीं जो ज़ाहिर हो, इश्क़ वो है जो महसूस हो। 💌",
                "तेरी बाहों में ही मेरा सारा जहां है। 💫"
            ],
            "medium": [
                "हज़ारों महफ़िलें हैं और लाखों मेले हैं, लेकिन जहाँ तुम नहीं वहाँ हम अकेले हैं। साथ तुम्हारा हमेशा दिल को सुकून देता है। ❤️🌹",
                "प्यार सिर्फ लफ़्ज़ों में बयां नहीं होता, यह तो खामोशियों में भी एक-दूसरे को समझ लेने का नाम है। 💌✨"
            ],
            "long": [
                "सच्चा प्यार वही है जो आपको अंदर से शांत और मजबूत बनाए। जब ज़िंदगी के हर मोड़ पर कोई ऐसा साथ हो जो बिना कहे आपके दिल की बात समझ ले, तो हर रास्ता आसान लगने लगता है। अपने खास इंसान को यह पोस्ट ज़रूर शेयर करें! ❤️🌹"
            ]
        }
    },
    "food": {
        "en": {
            "short": [
                "Food is my love language. 🍕❤️",
                "Life is uncertain. Eat dessert first. 🍰",
                "Good food = Good mood. 🍜",
                "Fork in one hand, happiness in the other. 🍔",
                "Calories don't count on the weekend."
            ],
            "medium": [
                "Pull up a chair and taste the magic. Cooking is love made edible, and this plate is pure joy. 🍝✨",
                "Surround yourself with pizza, not negativity. Nothing brings people together quite like unforgettable flavors. 🍕🔥"
            ],
            "long": [
                "They say you can't buy happiness, but you can buy delicious food, and that's basically the same thing. From the aromatic spices to the first mouthwatering bite, good food turns any ordinary day into a celebration. What's your all-time favorite comfort dish? Tell me below! 👇🍜"
            ]
        },
        "hi": {
            "short": [
                "स्वाद ऐसा जो दिल खुश कर दे। 🍜✨",
                "खाने के शौकीन हैं हम! 🍕😋",
                "ज़िन्दगी में स्वाद होना ज़रूरी है। 🍲",
                "गरमा-गरम खाना और ढेर सारा प्यार। 🍰"
            ],
            "medium": [
                "अच्छा खाना और अच्छी सोहबत, ज़िंदगी में इससे बेहतर और क्या हो सकता है? आज का खाना वाकई लाजवाब था! 🍛✨",
                "जब थाली में पसंदीदा खाना हो, तो दिन की सारी थकान मिट जाती है। आप सभी का पसंदीदा खाना क्या है? 🍕😋"
            ],
            "long": [
                "खाना सिर्फ भूख मिटाने के लिए नहीं होता, बल्कि यह पुरानी यादों और अपनों के प्यार को ताज़ा करने का जरिया है। चाहे माँ के हाथ का खाना हो या किसी ढाबे की चाय, स्वाद हमेशा दिल से जुड़ता है। आपका पसंदीदा स्ट्रीट फूड कौन सा है? नीचे कमेंट करें! 👇🍲"
            ]
        }
    }
}

class CaptionRequest(BaseModel):
    category: str = "travel"
    language: str = "en"
    length: str = "medium"

@router.post("/captions")
def generate_captions(req: CaptionRequest):
    cat = req.category.lower().strip()
    lang = req.language.lower().strip()
    length = req.length.lower().strip()

    if cat not in CAPTION_DATA:
        cat = "lifestyle"
    if lang not in ("en", "hi"):
        lang = "en"
    if length not in ("short", "medium", "long"):
        length = "medium"

    pool = CAPTION_DATA[cat][lang].get(length, [])
    # Return 3 to 5 options
    selected = random.sample(pool, min(len(pool), 4)) if pool else []
    if not selected and pool:
        selected = pool

    return {
        "success": True,
        "category": cat,
        "language": lang,
        "length": length,
        "captions": selected
    }


# ==========================================
# 2. HASHTAG GENERATOR
# ==========================================

HASHTAG_DATABASE: Dict[str, Dict[str, List[str]]] = {
    "travel": {
        "general": ["#travelgram", "#wanderlust", "#travelphotography", "#instatravel", "#travelblogger", "#exploretheworld", "#traveltheworld", "#passportready"],
        "niche": ["#solotraveler", "#backpackerlife", "#hikingadventures", "#mountainview", "#bucketlisttravel", "#hiddenplaces", "#scenicviews", "#roamtheplanet"],
        "location": ["#beautifuldestinations", "#travelusa", "#europetravel", "#exploreasia", "#travelcommunity", "#citybreak", "#naturelovers"]
    },
    "fitness": {
        "general": ["#fitnessmotivation", "#gymlife", "#fitfam", "#workoutroutine", "#trainingday", "#bodybuilding", "#fitgoals", "#healthylifestyle"],
        "niche": ["#strengthtraining", "#calisthenics", "#hiitworkout", "#gymrat", "#legdayworkout", "#cleaneating", "#gains", "#fitnessjourney"],
        "location": ["#gymmotivation", "#personaltrainer", "#homegym", "#outdoorfitness", "#fitnesslifestyle"]
    },
    "fashion": {
        "general": ["#fashioninspo", "#ootd", "#outfitoftheday", "#streetstyle", "#styleinspo", "#instafashion", "#fashionblogger", "#stylishlook"],
        "niche": ["#minimalfashion", "#capsulewardrobe", "#vintagestyle", "#thriftedfashion", "#chiclook", "#mensfashion", "#womenswear", "#sustainablefashion"],
        "location": ["#nycfashion", "#parisianstyle", "#londonstreetstyle", "#fashionaddict"]
    },
    "business": {
        "general": ["#entrepreneur", "#businessowner", "#startuplife", "#marketingstrategy", "#mindsetmatters", "#successmindset", "#smallbusiness", "#leadership"],
        "niche": ["#digitalmarketing", "#brandstrategy", "#growthhacking", "#financialfreedom", "#solopreneur", "#contentcreator", "#businessgrowth", "#sidehustle"],
        "location": ["#remotework", "#globalbusiness", "#creatoreconomy"]
    },
    "food": {
        "general": ["#foodporn", "#foodie", "#instafood", "#foodphotography", "#delicious", "#yummy", "#foodlover", "#chefmode"],
        "niche": ["#homemadefood", "#streetfood", "#plantbased", "#veganrecipes", "#bakinglove", "#comfortfood", "#tastydishes", "#dessertlover"],
        "location": ["#foodiesofinstagram", "#localcuisine", "#restaurantlife"]
    },
    "lifestyle": {
        "general": ["#lifestyleblogger", "#dailymoments", "#simpleliving", "#mindfulliving", "#gratitudeattitude", "#selfcarefirst", "#goodvibesonly"],
        "niche": ["#slowliving", "#aestheticvibes", "#cozyhome", "#wellnessjourney", "#morningroutine", "#positivevibes", "#peaceofmind"],
        "location": ["#lifestyleguide", "#weekendvibes", "#modernliving"]
    }
}

class HashtagRequest(BaseModel):
    category: str = "travel"
    niche: Optional[str] = None
    location: Optional[str] = None

@router.post("/hashtags")
def generate_hashtags(req: HashtagRequest):
    cat = req.category.lower().strip()
    if cat not in HASHTAG_DATABASE:
        cat = "lifestyle"

    data = HASHTAG_DATABASE[cat]
    general_tags = random.sample(data["general"], min(len(data["general"]), 6))
    niche_tags = random.sample(data["niche"], min(len(data["niche"]), 6))
    location_tags = random.sample(data["location"], min(len(data["location"]), 4))

    custom_tags = []
    if req.niche and req.niche.strip():
        clean_n = re.sub(r"[^A-Za-z0-9]", "", req.niche.strip())
        if clean_n:
            custom_tags.append(f"#{clean_n.lower()}")
            custom_tags.append(f"#{clean_n.lower()}tips")
            custom_tags.append(f"#{clean_n.lower()}community")

    if req.location and req.location.strip():
        clean_loc = re.sub(r"[^A-Za-z0-9]", "", req.location.strip())
        if clean_loc:
            custom_tags.append(f"#{clean_loc.lower()}")
            custom_tags.append(f"#{clean_loc.lower()}life")

    all_tags = list(dict.fromkeys(general_tags + niche_tags + location_tags + custom_tags))

    return {
        "success": True,
        "category": cat,
        "groups": {
            "top_relevance": general_tags,
            "niche_specific": niche_tags + custom_tags[:2],
            "community_location": location_tags + custom_tags[2:]
        },
        "all_tags": all_tags,
        "copy_text": " ".join(all_tags)
    }


# ==========================================
# 3. BIO GENERATOR
# ==========================================

class BioRequest(BaseModel):
    bio_type: str = "personal" # personal, creator, business, minimal
    niche: Optional[str] = "Creator"
    name: Optional[str] = None
    include_emoji: bool = True

BIO_TEMPLATES = {
    "personal": [
        {"emoji": "✨ {name}\n📍 Exploring life one day at a time\n☕ Coffee & good conversations\n💌 DM for collabs", "clean": "{name}\nExploring life one day at a time\nCoffee and good conversations\nDM for collaborations"},
        {"emoji": "🌿 Just living in the sunshine\n📸 Capturing moments, big and small\n✨ Grateful for every chapter", "clean": "Living in the sunshine\nCapturing moments, big and small\nGrateful for every chapter"},
        {"emoji": "🚀 Chasing horizons\n🎧 Music on, world off\n💫 Living unapologetically", "clean": "Chasing horizons\nMusic on, world off\nLiving unapologetically"}
    ],
    "creator": [
        {"emoji": "🎯 Helping you master {niche}\n💡 Daily tips, workflows & strategies\n👇 Join 10k+ creators reading my guide", "clean": "Helping you master {niche}\nDaily tips, workflows, and strategies\nRead my creator guide below"},
        {"emoji": "🎬 {niche} Creator & Visual Storyteller\n⚡ Building something cool every week\n📩 Work with me: link below", "clean": "{niche} Creator & Visual Storyteller\nBuilding innovative projects every week\nWork with me: link below"},
        {"emoji": "🔥 High-impact insights on {niche}\n📈 Simplifying growth for modern builders\n👇 Grab the free toolkit", "clean": "High-impact insights on {niche}\nSimplifying growth for modern builders\nAccess the free toolkit below"}
    ],
    "business": [
        {"emoji": "💼 Premium {niche} Solutions\n🌟 Trusted by 5,000+ happy clients\n📦 Worldwide shipping & 24/7 support\n👇 Shop our collection", "clean": "Premium {niche} Solutions\nTrusted by 5,000+ satisfied clients\nWorldwide shipping and support\nShop our collection below"},
        {"emoji": "🏢 Empowering brands through {niche}\n📈 Proven strategies that drive results\n📅 Book your free consultation 👇", "clean": "Empowering brands through {niche}\nProven strategies that drive results\nBook your free discovery call below"},
        {"emoji": "✨ Elevate your everyday with {niche}\n🌿 Ethically crafted & sustainably made\n👇 Discover new arrivals", "clean": "Elevate your everyday with {niche}\nEthically crafted & sustainably made\nDiscover our newest arrivals below"}
    ],
    "minimal": [
        {"emoji": "simplicity is the ultimate sophistication. 🕊️\n{niche} • digital archives", "clean": "simplicity is the ultimate sophistication.\n{niche} / digital archives"},
        {"emoji": "less is more. ☕\nquietly building.", "clean": "less is more.\nquietly building."},
        {"emoji": "documented, not created. ✨\n{niche}", "clean": "documented, not created.\n{niche}"}
    ]
}

@router.post("/bio")
def generate_bios(req: BioRequest):
    btype = req.bio_type.lower().strip()
    if btype not in BIO_TEMPLATES:
        btype = "personal"

    niche = req.niche.strip() if req.niche else "Creator"
    name = req.name.strip() if req.name else "Creative Soul"

    templates = BIO_TEMPLATES[btype]
    results = []
    for t in templates:
        txt = t["emoji"] if req.include_emoji else t["clean"]
        formatted = txt.replace("{niche}", niche).replace("{name}", name)
        results.append(formatted)

    return {
        "success": True,
        "bio_type": btype,
        "bios": results
    }


# ==========================================
# 4. USERNAME GENERATOR
# ==========================================

USERNAME_PREFIXES = ["the", "its", "iam", "hey", "meet", "by", "real", "club", "studio", "daily"]
USERNAME_SUFFIXES = ["vibe", "craft", "hub", "daily", "zone", "official", "co", "lab", "hq", "space"]

class UsernameRequest(BaseModel):
    base_keyword: str
    category: str = "creator" # personal, creator, business

@router.post("/usernames")
def generate_usernames(req: UsernameRequest):
    base = re.sub(r"[^A-Za-z0-9]", "", req.base_keyword.strip().lower())
    if not base:
        base = "creator"

    cat = req.category.lower().strip()

    ideas = [
        f"the.{base}",
        f"{base}.official",
        f"its{base}",
        f"{base}_hq",
        f"{base}.studio",
        f"{base}daily",
        f"meet{base}",
        f"{base}vibe",
        f"real.{base}",
        f"{base}.craft",
        f"{base}_co",
        f"by{base}"
    ]

    if cat == "business":
        ideas = [
            f"{base}.co",
            f"{base}_group",
            f"the{base}co",
            f"{base}.solutions",
            f"{base}studio",
            f"get{base}",
            f"{base}.hq",
            f"{base}global"
        ]
    elif cat == "personal":
        ideas = [
            f"iam{base}",
            f"{base}.raw",
            f"just{base}",
            f"{base}_vibes",
            f"heyits{base}",
            f"{base}.life",
            f"not{base}"
        ]

    return {
        "success": True,
        "base_keyword": base,
        "category": cat,
        "usernames": ideas,
        "disclaimer": "Username ideas are generated creatively. Please check live availability in the Instagram app before creating accounts."
    }


# ==========================================
# 5. REEL HOOK GENERATOR
# ==========================================

REEL_HOOKS = {
    "educational": {
        "en": [
            "Stop doing {topic} the hard way. Here is the 2-minute shortcut:",
            "3 mistakes everyone makes when starting {topic} (and how to fix them):",
            "I spent 100 hours learning {topic} so you don't have to:",
            "This secret {topic} trick feels illegal to know:",
            "The simplest framework for {topic} that actually works:"
        ],
        "hi": [
            "{topic} सीखने का सबसे आसान तरीका जो कोई नहीं बताता:",
            "{topic} करते समय ये 3 गलतियाँ कभी मत करना:",
            "अगर आप {topic} में सफल होना चाहते हैं, तो यह वीडियो अंत तक देखें:",
            "सिर्फ 60 सेकंड में समझें {topic} का पूरा सच:"
        ]
    },
    "storytelling": {
        "en": [
            "I almost gave up on {topic} until this happened...",
            "Nobody believed me when I said this about {topic}:",
            "The untold story behind how I mastered {topic}:",
            "This single moment completely changed how I look at {topic}:"
        ],
        "hi": [
            "जब मैंने {topic} शुरू किया, तो सबने मना किया था... लेकिन फिर:",
            "एक छोटी सी सीख जिसने मेरी ज़िंदगी बदल दी ({topic}):",
            "यह गलती मुझे बहुत भारी पड़ी, आप मत दोहराना:"
        ]
    },
    "business": {
        "en": [
            "How we scaled {topic} without spending a dollar on ads:",
            "If you want to monetize {topic} in 2026, watch this:",
            "The exact pricing strategy I used for {topic}:",
            "Why 90% of people fail at {topic} (and how to be the 10%):"
        ],
        "hi": [
            "{topic} से घर बैठे पैसे कमाने का सही तरीका:",
            "2026 में {topic} का बिज़नेस कैसे शुरू करें:",
            "अगर आपका बजट कम है, तो {topic} ऐसे शुरू करें:"
        ]
    },
    "entertainment": {
        "en": [
            "Tell me I'm not the only one who does this with {topic} 😂",
            "Rating {topic} trends from 1 to 10 (don't get mad):",
            "POV: You finally figure out how {topic} works:",
            "Things that just make sense when dealing with {topic}:"
        ],
        "hi": [
            "जब आप पहली बार {topic} ट्राई करते हैं 😂",
            "ये सिर्फ वही समझेंगे जो {topic} से जुड़े हैं:",
            "देखते हैं कितने लोग इस बात से सहमत हैं 👇"
        ]
    }
}

class HookRequest(BaseModel):
    category: str = "educational"
    topic: str = "content creation"
    language: str = "en"

@router.post("/reel-hooks")
def generate_reel_hooks(req: HookRequest):
    cat = req.category.lower().strip()
    lang = req.language.lower().strip()
    if cat not in REEL_HOOKS:
        cat = "educational"
    if lang not in ("en", "hi"):
        lang = "en"

    topic = req.topic.strip() or "Instagram"
    templates = REEL_HOOKS[cat].get(lang, REEL_HOOKS[cat]["en"])

    hooks = [t.replace("{topic}", topic) for t in templates]

    return {
        "success": True,
        "category": cat,
        "language": lang,
        "hooks": hooks
    }


# ==========================================
# 6. POST IDEA GENERATOR
# ==========================================

POST_IDEAS = {
    "fitness": {
        "reels": [
            "3 Mobility exercises to do before your morning coffee",
            "What I eat in a day as a busy professional (realistic version)",
            "Common squat form mistake and how to fix it in 10 seconds",
            "Gym bag essentials that actually matter"
        ],
        "carousels": [
            "Beginner's Guide: How to structure your first workout week",
            "5 High-protein snacks you can prep in under 10 minutes",
            "Myth buster: Cardio vs Weights for fat loss explained visually"
        ],
        "calendar": [
            "Monday: Motivation & workout breakdown",
            "Wednesday: Technique tutorial / form fix",
            "Friday: Nutrition tip or healthy meal idea",
            "Sunday: Weekly reflection & rest day mobility"
        ]
    },
    "business": {
        "reels": [
            "3 Software tools that save me 10 hours every week",
            "How I structure my working day for maximum deep work",
            "The hardest lesson I learned losing a major client"
        ],
        "carousels": [
            "The 5-step funnel every small business needs in 2026",
            "Before vs After: Website redesign case study with metrics",
            "How to write cold emails that actually get answered"
        ],
        "calendar": [
            "Monday: Case study or customer transformation",
            "Wednesday: Tactical tutorial / workflow breakdown",
            "Friday: Industry news analysis or opinion piece",
            "Saturday: Behind the scenes / founder story"
        ]
    },
    "travel": {
        "reels": [
            "Hidden gem in [City] that tourist guides never mention",
            "What $50 gets you in [Country] (Street food tour)",
            "Packing hack: How to fit 2 weeks into a single carry-on"
        ],
        "carousels": [
            "The ultimate 3-day itinerary for [Destination]",
            "10 Essential travel apps you need to download right now",
            "Cost breakdown of our trip to [Country] (Hotel, Food, Travel)"
        ],
        "calendar": [
            "Tuesday: City guide / hidden cafe spotlight",
            "Thursday: Budget breakdown or packing hack",
            "Sunday: High-resolution photo collection with travel story"
        ]
    },
    "creator": {
        "reels": [
            "My exact lighting setup for under $100",
            "How to edit videos 2x faster with this keyboard shortcut",
            "The difference between good hooks and scroll-stopping hooks"
        ],
        "carousels": [
            "Instagram Algorithm in 2026: What signals matter most",
            "10 Carousel design templates you can steal right now",
            "How to repurpose 1 long video into 5 short-form posts"
        ],
        "calendar": [
            "Monday: Practical tutorial / tech breakdown",
            "Wednesday: Carousel blueprint or infographic",
            "Friday: Content creation tool review",
            "Sunday: Weekly learnings & creator mindsets"
        ]
    }
}

class PostIdeaRequest(BaseModel):
    niche: str = "creator"

@router.post("/post-ideas")
def generate_post_ideas(req: PostIdeaRequest):
    niche = req.niche.lower().strip()
    if niche not in POST_IDEAS:
        niche = "creator"

    data = POST_IDEAS[niche]
    return {
        "success": True,
        "niche": niche,
        "reel_ideas": data["reels"],
        "carousel_ideas": data["carousels"],
        "calendar_suggestions": data["calendar"]
    }


# ==========================================
# 7. CAPTION FORMATTER
# ==========================================

# Mathematical alphanumeric symbols for stylish text
UNICODE_MAPS = {
    "bold_sans": {
        "a": "𝗮", "b": "𝗯", "c": "𝗰", "d": "𝗱", "e": "𝗲", "f": "𝗳", "g": "𝗴", "h": "𝗵", "i": "𝗶", "j": "𝗷",
        "k": "𝗸", "l": "𝗹", "m": "𝗺", "n": "𝗻", "o": "𝗼", "p": "𝗽", "q": "𝗾", "r": "𝗿", "s": "𝘀", "t": "𝘁",
        "u": "𝘂", "v": "𝘃", "w": "𝘄", "x": "𝘅", "y": "𝘆", "z": "𝘇",
        "A": "𝗔", "B": "𝗕", "C": "𝗖", "D": "𝗗", "E": "𝗘", "F": "𝗙", "G": "𝗚", "H": "𝗛", "I": "𝗜", "J": "𝗝",
        "K": "𝗞", "L": "𝗟", "M": "𝗠", "N": "𝗡", "O": "𝗢", "P": "𝗣", "Q": "𝗤", "R": "𝗥", "S": "𝗦", "T": "𝗧",
        "U": "𝗨", "V": "𝗩", "W": "𝗪", "X": "𝗫", "Y": "𝗬", "Z": "𝗭",
        "0": "𝟬", "1": "𝟭", "2": "𝟮", "3": "𝟯", "4": "𝟰", "5": "𝟱", "6": "𝟲", "7": "𝟳", "8": "𝟴", "9": "𝟵"
    },
    "italic_serif": {
        "a": "𝑎", "b": "𝑏", "c": "𝑐", "d": "𝑑", "e": "𝑒", "f": "𝑓", "g": "𝑔", "h": "ℎ", "i": "𝑖", "j": "𝑗",
        "k": "𝑘", "l": "𝑙", "m": "𝑚", "n": "𝑛", "o": "𝑜", "p": "𝑝", "q": "𝑞", "r": "𝑟", "s": "𝑠", "t": "𝑡",
        "u": "𝑢", "v": "𝑣", "w": "𝑤", "x": "𝑥", "y": "𝑦", "z": "𝑧",
        "A": "𝐴", "B": "𝐵", "C": "𝐶", "D": "𝐷", "E": "𝐸", "F": "𝐹", "G": "𝐺", "H": "𝐻", "I": "𝐼", "J": "𝐽",
        "K": "𝐾", "L": "𝐿", "M": "𝑀", "N": "𝑁", "O": "𝑂", "P": "𝑃", "Q": "𝑄", "R": "𝑅", "S": "𝑆", "T": "𝑇",
        "U": "𝑈", "V": "𝑉", "W": "𝑊", "X": "𝑋", "Y": "𝑌", "Z": "𝑍"
    },
    "typewriter": {
        "a": "𝚊", "b": "𝚋", "c": "𝚌", "d": "𝚍", "e": "𝚎", "f": "𝚏", "g": "𝚐", "h": "𝚑", "i": "𝚒", "j": "𝚓",
        "k": "𝚔", "l": "𝚕", "m": "𝚖", "n": "𝚗", "o": "𝚘", "p": "𝚙", "q": "𝚚", "r": "𝚛", "s": "𝚜", "t": "𝚝",
        "u": "𝚞", "v": "𝚟", "w": "𝚠", "x": "𝚡", "y": "𝚢", "z": "𝚣",
        "A": "𝙰", "B": "𝙱", "C": "𝙲", "D": "𝙳", "E": "𝙴", "F": "𝙵", "G": "𝙶", "H": "𝙷", "I": "𝙸", "J": "𝙹",
        "K": "𝙺", "L": "𝙻", "M": "𝙼", "N": "𝙽", "O": "𝙾", "P": "𝙿", "Q": "𝚀", "R": "𝚁", "S": "𝚂", "T": "𝚃",
        "U": "𝚄", "V": "𝚅", "W": "𝚆", "X": "𝚇", "Y": "𝚈", "Z": "𝚉"
    },
    "script": {
        "a": "𝒶", "b": "𝒷", "c": "𝒸", "d": "𝒹", "e": "ℯ", "f": "𝒻", "g": "ℊ", "h": "𝒽", "i": "𝒾", "j": "𝒿",
        "k": "𝓀", "l": "𝓁", "m": "𝓂", "n": "𝓃", "o": "ℴ", "p": "𝓅", "q": "𝓆", "r": "𝓇", "s": "𝓈", "t": "𝓉",
        "u": "𝓊", "v": "𝓋", "w": "𝓌", "x": "𝓍", "y": "𝓎", "z": "𝓏",
        "A": "𝒜", "B": "ℬ", "C": "𝒞", "D": "𝒟", "E": "ℰ", "F": "ℱ", "G": "𝒢", "H": "ℋ", "I": "ℐ", "J": "𝒥",
        "K": "𝒦", "L": "ℒ", "M": "ℳ", "N": "𝒩", "O": "𝒪", "P": "𝒫", "Q": "𝒬", "R": "ℛ", "S": "𝒮", "T": "𝒯",
        "U": "𝒰", "V": "𝒱", "W": "𝒲", "X": "𝒳", "Y": "𝒴", "Z": "𝒵"
    }
}

class FormatRequest(BaseModel):
    text: str
    style: str = "clean" # clean, bold_sans, italic_serif, typewriter, script, spaced

def transform_unicode(text: str, map_dict: Dict[str, str]) -> str:
    return "".join(map_dict.get(c, c) for c in text)

@router.post("/format")
def format_caption(req: FormatRequest):
    raw = req.text.strip()
    if not raw:
        return {"success": True, "formatted_text": ""}

    # 1. Clean line breaks: inject non-breaking whitespace to prevent Instagram line collapsing
    # Normalize double linebreaks with zero-width or braille space
    lines = raw.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            # Clean invisible blank line for Instagram
            cleaned_lines.append("⠀")
        else:
            cleaned_lines.append(stripped)

    clean_text = "\n".join(cleaned_lines)

    # 2. Apply typography transformation if requested
    style = req.style.lower().strip()
    if style in UNICODE_MAPS:
        formatted = transform_unicode(clean_text, UNICODE_MAPS[style])
    elif style == "spaced":
        formatted = " ".join(list(clean_text))
    else:
        formatted = clean_text

    char_count = len(formatted)
    word_count = len(re.findall(r"\w+", formatted))

    return {
        "success": True,
        "style": style,
        "formatted_text": formatted,
        "char_count": char_count,
        "word_count": word_count,
        "fits_instagram_limit": char_count <= 2200
    }


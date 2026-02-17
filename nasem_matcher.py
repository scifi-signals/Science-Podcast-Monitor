# nasem_matcher.py
# Matches trending topics to NASEM publications and current projects
# Uses both scraped catalog (1300+ publications) and hand-curated keywords
# Improved with title-based keyword extraction and semantic matching

import re
import os
import json
from llm import ask_llm

# Topic expansion: maps broad topics to related specific terms for better matching
# When searching for "space", also search for "mars", "moon", etc.
TOPIC_EXPANSIONS = {
    'space': ['mars', 'moon', 'lunar', 'planetary', 'nasa', 'asteroid', 'satellite', 'rocket', 'spaceflight'],
    'astronomy': ['telescope', 'exoplanet', 'galaxy', 'cosmic', 'stellar', 'astrophysics'],
    'climate': ['carbon', 'emissions', 'warming', 'greenhouse', 'weather', 'temperature'],
    'health': ['disease', 'medical', 'patient', 'treatment', 'hospital', 'clinical'],
    'genetics': ['gene', 'genome', 'dna', 'crispr', 'hereditary', 'mutation'],
    'infectious': ['virus', 'bacteria', 'pathogen', 'outbreak', 'epidemic', 'pandemic'],
    'aging': ['elderly', 'older adults', 'longevity', 'dementia', 'alzheimer'],
    'vaccine': ['immunization', 'vaccination', 'antibody', 'immune'],
    'evolution': ['fossil', 'paleontology', 'ancient', 'prehistoric', 'darwin'],
    'polar': ['arctic', 'antarctic', 'ice', 'glacier', 'permafrost'],
}

# Try to load scraped catalog if available
SCRAPED_CATALOG = []
CURRENT_PROJECTS = []
try:
    catalog_path = os.path.join(os.path.dirname(__file__), 'nasem_catalog.json')
    if os.path.exists(catalog_path):
        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog_data = json.load(f)
            SCRAPED_CATALOG = catalog_data.get('publications', [])
            CURRENT_PROJECTS = catalog_data.get('current_projects', [])
            print(f"  Loaded {len(SCRAPED_CATALOG)} publications + {len(CURRENT_PROJECTS)} current projects")
except Exception:
    pass

# Hand-curated keywords for important publications (supplements scraped data)
# These have more precise domain keywords than auto-extracted ones
VERIFIED_PUBLICATIONS = [
    # AI and Computing
    {"id": "27644", "title": "Artificial Intelligence and the Future of Work", "keywords": ["artificial intelligence", "ai", "work", "labor", "automation", "jobs"]},
    {"id": "26355", "title": "Human-AI Teaming: State-of-the-Art and Research Needs", "keywords": ["artificial intelligence", "ai", "human", "teaming", "collaboration", "machine learning"]},
    {"id": "26887", "title": "Artificial Intelligence and Justified Confidence", "keywords": ["artificial intelligence", "ai", "confidence", "trust", "machine learning"]},
    {"id": "25303", "title": "Reproducibility and Replicability in Science", "keywords": ["science", "research", "reproducibility", "replicability", "methodology", "scientific"]},

    # Quantum Computing
    {"id": "25196", "title": "Quantum Computing: Progress and Prospects", "keywords": ["quantum", "computing", "qubit", "quantum computer", "quantum mechanics", "cryptography"]},

    # Cybersecurity
    {"id": "11925", "title": "Toward a Safer and More Secure Cyberspace", "keywords": ["cybersecurity", "cyber", "security", "hacking", "computer security", "digital"]},
    {"id": "18749", "title": "At the Nexus of Cybersecurity and Public Policy", "keywords": ["cybersecurity", "cyber", "policy", "security", "digital", "internet"]},
    {"id": "24676", "title": "Foundational Cybersecurity Research", "keywords": ["cybersecurity", "cyber", "research", "security", "computer", "digital"]},

    # Climate and Environment
    {"id": "18373", "title": "Abrupt Impacts of Climate Change: Anticipating Surprises", "keywords": ["climate", "climate change", "environment", "abrupt", "warming", "global"]},
    {"id": "25733", "title": "Climate Change: Evidence and Causes: Update 2020", "keywords": ["climate", "climate change", "evidence", "global warming", "environment", "carbon"]},
    {"id": "18726", "title": "The Arctic in the Anthropocene: Emerging Research Questions", "keywords": ["arctic", "climate", "environment", "polar", "ice", "anthropocene", "north"]},
    {"id": "18988", "title": "Climate Intervention: Reflecting Sunlight to Cool Earth", "keywords": ["climate", "geoengineering", "solar", "intervention", "cooling", "albedo"]},
    {"id": "25259", "title": "Negative Emissions Technologies and Reliable Sequestration", "keywords": ["carbon", "emissions", "sequestration", "climate", "carbon capture", "negative emissions"]},

    # Energy and Decarbonization
    {"id": "25932", "title": "Accelerating Decarbonization of the U.S. Energy System", "keywords": ["energy", "decarbonization", "renewable", "clean energy", "carbon", "electricity"]},
    {"id": "12619", "title": "Electricity from Renewable Resources: Status, Prospects, and Impediments", "keywords": ["renewable", "energy", "solar", "wind", "electricity", "clean energy"]},

    # Nuclear Fusion
    {"id": "25331", "title": "Final Report: Strategic Plan for U.S. Burning Plasma Research", "keywords": ["fusion", "nuclear fusion", "plasma", "energy", "iter", "tokamak"]},
    {"id": "18289", "title": "An Assessment of the Prospects for Inertial Fusion Energy", "keywords": ["fusion", "inertial fusion", "energy", "nuclear", "laser", "ignition"]},

    # Space and Astronomy
    {"id": "26522", "title": "Origins, Worlds, and Life: A Decadal Strategy for Planetary Science", "keywords": ["planetary", "space", "astrobiology", "planets", "solar system", "nasa", "exploration", "astronomy", "mars", "moon", "asteroid", "telescope"]},

    # Ocean Science
    {"id": "27846", "title": "Forecasting the Ocean: The 2025-2035 Decade of Ocean Science", "keywords": ["ocean", "marine", "sea", "oceanography", "coastal", "marine science"]},
    {"id": "21655", "title": "Sea Change: 2015-2025 Decadal Survey of Ocean Sciences", "keywords": ["ocean", "marine", "oceanography", "sea", "coastal", "marine biology"]},
    {"id": "26132", "title": "Reckoning with the U.S. Role in Global Ocean Plastic Waste", "keywords": ["plastic", "microplastic", "ocean", "pollution", "waste", "marine debris"]},

    # Wildfires
    {"id": "25622", "title": "Implications of the California Wildfires for Health, Communities, and Preparedness", "keywords": ["wildfire", "fire", "california", "forest fire", "smoke", "disaster"]},
    {"id": "26460", "title": "The Chemistry of Fires at the Wildland-Urban Interface", "keywords": ["wildfire", "fire", "urban", "chemistry", "combustion", "wui"]},
    {"id": "27972", "title": "Social-Ecological Consequences of Future Wildfires and Smoke in the West", "keywords": ["wildfire", "fire", "smoke", "west", "forest", "climate"]},

    # Health and Medicine
    {"id": "24624", "title": "Communities in Action: Pathways to Health Equity", "keywords": ["health", "equity", "community", "public health", "disparities", "social"]},
    {"id": "10027", "title": "Crossing the Quality Chasm: A New Health System for the 21st Century", "keywords": ["health", "healthcare", "medical", "quality", "system", "hospital"]},
    {"id": "13284", "title": "Toward Precision Medicine: Building a Knowledge Network", "keywords": ["precision medicine", "personalized", "medical", "genomic", "health", "treatment"]},
    {"id": "13006", "title": "What You Need to Know About Infectious Disease", "keywords": ["infectious", "disease", "infection", "virus", "bacteria", "pathogen", "epidemic"]},
    {"id": "26350", "title": "Combating Antimicrobial Resistance and Protecting Modern Medicine", "keywords": ["antimicrobial", "antibiotic", "resistance", "bacteria", "infection", "drug"]},
    {"id": "25310", "title": "Medications for Opioid Use Disorder Save Lives", "keywords": ["opioid", "addiction", "medication", "treatment", "drug", "overdose"]},
    {"id": "12089", "title": "Retooling for an Aging America: Building the Health Care Workforce", "keywords": ["aging", "elderly", "older adults", "healthcare", "workforce", "age", "senior"]},

    # Mental Health
    {"id": "26015", "title": "Mental Health, Substance Use, and Wellbeing in Higher Education", "keywords": ["mental health", "psychology", "substance use", "wellbeing", "college", "students"]},
    {"id": "26175", "title": "Reducing the Impact of Dementia in America: A Decadal Survey", "keywords": ["dementia", "alzheimer", "cognitive", "brain", "aging", "memory"]},
    {"id": "28588", "title": "Preventing and Treating Dementia: Research Priorities to Accelerate Progress", "keywords": ["dementia", "alzheimer", "treatment", "prevention", "brain", "cognitive"]},

    # Neuroscience
    {"id": "1816", "title": "Mapping the Brain and Its Functions", "keywords": ["brain", "neuroscience", "neurology", "neural", "cognitive", "mapping"]},
    {"id": "1785", "title": "Discovering the Brain", "keywords": ["brain", "neuroscience", "neurology", "cognitive", "neural", "mind"]},

    # Cancer
    {"id": "11468", "title": "From Cancer Patient to Cancer Survivor: Lost in Transition", "keywords": ["cancer", "survivor", "oncology", "treatment", "patient", "tumor"]},
    {"id": "21841", "title": "Ovarian Cancers: Evolving Paradigms in Research and Care", "keywords": ["cancer", "ovarian", "oncology", "tumor", "treatment", "women"]},
    {"id": "10107", "title": "Mammography and Beyond: Developing Technologies for Early Detection of Breast Cancer", "keywords": ["cancer", "breast cancer", "mammography", "screening", "detection", "women"]},

    # Pandemic Preparedness
    {"id": "21891", "title": "The Neglected Dimension of Global Security: A Framework to Counter Infectious Disease Crises", "keywords": ["pandemic", "infectious disease", "outbreak", "epidemic", "preparedness", "global health"]},
    {"id": "26301", "title": "Systematizing the One Health Approach in Preparedness and Response", "keywords": ["pandemic", "one health", "preparedness", "outbreak", "zoonotic", "disease"]},
    {"id": "25391", "title": "Exploring Lessons Learned from a Century of Outbreaks: Readiness for 2030", "keywords": ["pandemic", "outbreak", "epidemic", "preparedness", "infectious", "disease"]},
    {"id": "26284", "title": "Countering the Pandemic Threat Through Global Coordination on Vaccines", "keywords": ["pandemic", "vaccine", "global", "coordination", "influenza", "preparedness"]},

    # Genetics and Genomics
    {"id": "24632", "title": "An Evidence Framework for Genetic Testing", "keywords": ["genetic", "genetics", "testing", "dna", "genomic", "screening"]},
    {"id": "26902", "title": "Using Population Descriptors in Genetics and Genomics Research", "keywords": ["genetic", "genomic", "population", "diversity", "ancestry", "dna"]},
    {"id": "5955", "title": "Evaluating Human Genetic Diversity", "keywords": ["genetic", "diversity", "human", "population", "dna", "genome"]},

    # Evolution and Origins of Life
    {"id": "11876", "title": "Science, Evolution, and Creationism", "keywords": ["evolution", "evolutionary", "biology", "science", "origins", "natural selection"]},
    {"id": "12161", "title": "Origin and Evolution of Earth: Research Questions for a Changing Planet", "keywords": ["evolution", "earth", "geology", "planet", "origins", "geological"]},
    {"id": "1541", "title": "The Search for Life's Origins: Progress and Future Directions", "keywords": ["origins", "life", "astrobiology", "evolution", "biology", "prebiotic"]},

    # Biodiversity and Conservation
    {"id": "989", "title": "Biodiversity", "keywords": ["biodiversity", "species", "ecosystem", "conservation", "ecology", "wildlife"]},
    {"id": "1925", "title": "Conserving Biodiversity: A Research Agenda for Development", "keywords": ["biodiversity", "conservation", "ecology", "species", "environment", "wildlife"]},

    # Vaccines and Immunity
    {"id": "10306", "title": "Immunization Safety Review: Multiple Immunizations and Immune Dysfunction", "keywords": ["vaccine", "immunization", "immune", "immunity", "safety", "vaccination"]},

    # Research and Academia
    {"id": "25038", "title": "Graduate STEM Education for the 21st Century", "keywords": ["education", "stem", "graduate", "phd", "academic", "university", "students"]},
    {"id": "18944", "title": "SBIR at the National Science Foundation", "keywords": ["research", "nsf", "funding", "science", "sbir", "grants", "innovation"]},
    {"id": "12154", "title": "Challenges and Successes in Reducing Health Disparities", "keywords": ["health", "disparities", "equity", "community", "minority"]},
]

# Common words to skip when extracting keywords from titles
TITLE_STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of',
    'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'toward', 'towards', 'into', 'about', 'through', 'during', 'before', 'after',
    'above', 'below', 'between', 'under', 'over', 'out', 'off', 'up', 'down',
    'new', 'future', 'state', 'states', 'united', 'national', 'report', 'reports',
    'study', 'studies', 'research', 'review', 'summary', 'framework', 'approach',
    'proceedings', 'workshop', 'needs', 'issues', 'challenges', 'opportunities',
    '21st', 'century', 'update', 'agenda', 'action', 'building', 'developing',
    'assessment', 'evaluation', 'implications', 'strategies', 'pathways', 'perspectives',
}


def extract_keywords_from_title(title):
    """Extract meaningful keywords from a publication title."""
    # Clean and split title
    words = re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())

    # Filter out stop words and return unique keywords
    keywords = []
    for word in words:
        if word not in TITLE_STOP_WORDS and len(word) >= 4:
            keywords.append(word)

    # Also extract 2-word phrases that might be meaningful
    title_lower = title.lower()
    meaningful_phrases = [
        'artificial intelligence', 'machine learning', 'climate change', 'gene therapy',
        'cancer research', 'stem cells', 'public health', 'mental health', 'nuclear energy',
        'quantum computing', 'infectious disease', 'drug discovery', 'precision medicine',
        'renewable energy', 'carbon emissions', 'biodiversity loss', 'food security',
        'water quality', 'air pollution', 'opioid crisis', 'vaccine safety', 'gene editing',
        'ocean science', 'space exploration', 'arctic research', 'wildfire', 'pandemic',
        'antibiotic resistance', 'global health', 'health equity', 'brain science',
        'neuroscience', 'alzheimer', 'dementia', 'diabetes', 'obesity', 'aging population',
    ]
    for phrase in meaningful_phrases:
        if phrase in title_lower and phrase not in keywords:
            keywords.append(phrase)

    return keywords


def llm_semantic_match(topic_name, candidate_titles, max_titles=10):
    """Use LLM to find semantically related publications from candidates."""
    if not candidate_titles:
        return []

    # Limit the number of candidates to check
    titles_to_check = candidate_titles[:max_titles]
    titles_str = "\n".join([f"{i+1}. {t}" for i, t in enumerate(titles_to_check)])

    prompt = f"""Given this trending news topic: "{topic_name}"

Rate which of these NASEM publications are most relevant (0-10 scale):

{titles_str}

Return ONLY a comma-separated list of the publication numbers that score 7 or higher.
For example: "1, 4, 7" or "none" if no publications are relevant.
No explanation needed."""

    try:
        response = ask_llm(prompt)
        response = response.strip().lower()

        if 'none' in response or not response:
            return []

        # Parse the numbers
        numbers = re.findall(r'\d+', response)
        indices = [int(n) - 1 for n in numbers if 0 <= int(n) - 1 < len(titles_to_check)]

        return indices
    except Exception:
        return []


def score_publication(pub, topic_lower, topic_words):
    """
    Score a publication against a topic using enriched metadata.

    Returns (total_score, breakdown) where breakdown has component scores.
    """
    keyword_score = 0
    title_score = 0
    description_score = 0
    recency_score = 0

    # Get keywords - handle both scraped format and hand-curated format
    keywords = pub.get("keywords", [])
    if isinstance(keywords, str):
        keywords = [keywords]

    # If no keywords, extract from title
    if not keywords:
        keywords = extract_keywords_from_title(pub.get("title", ""))

    # Check if any keyword appears in the topic (primary match)
    for keyword in keywords:
        keyword_lower = keyword.lower()
        if keyword_lower in topic_lower:
            # Longer keyword matches are more valuable
            if len(keyword) >= 12:
                keyword_score += 6  # Very specific match (e.g., "climate change")
            elif len(keyword) >= 8:
                keyword_score += 4  # Strong match (e.g., "immunotherapy")
            else:
                keyword_score += 2  # Regular match
        # Check if keyword matches any expanded topic word (e.g., "mars" when topic is "space")
        elif keyword_lower in topic_words:
            keyword_score += 3  # Good match via expansion
        # Also check reverse: topic words in keyword (catches phrase matches)
        elif any(word in keyword_lower for word in topic_words if len(word) >= 5):
            keyword_score += 1

    # Check if any word from the topic appears in the title (secondary)
    title_lower = pub.get("title", "").lower()
    for word in topic_words:
        # Use word boundary matching to avoid partial matches
        if re.search(r'\b' + re.escape(word) + r'\b', title_lower):
            title_score += 1.5  # Title word match (slightly boosted)

    # Check description for matches (new enriched field)
    description = pub.get("description", "").lower()
    if description:
        for word in topic_words:
            if len(word) >= 5 and re.search(r'\b' + re.escape(word) + r'\b', description):
                description_score += 0.5  # Description matches worth less than title

    # Recency bonus (new enriched field)
    year = pub.get("year", 0)
    if year:
        from datetime import datetime
        current_year = datetime.now().year
        age = current_year - year
        if age <= 2:
            recency_score = 3  # Very recent (last 2 years)
        elif age <= 5:
            recency_score = 2  # Recent (last 5 years)
        elif age <= 10:
            recency_score = 1  # Moderately recent

    total_score = keyword_score + title_score + description_score + recency_score

    return total_score, {
        'keyword': keyword_score,
        'title': title_score,
        'description': description_score,
        'recency': recency_score
    }


def expand_topic_words(topic_words):
    """Expand topic words with related terms for better matching."""
    expanded = set(topic_words)
    for word in topic_words:
        if word in TOPIC_EXPANSIONS:
            expanded.update(TOPIC_EXPANSIONS[word])
    return expanded


def find_publications_for_topic(topic_name, use_llm_fallback=True):
    """Find relevant publications from both hand-curated and scraped sources."""
    topic_lower = topic_name.lower()
    topic_words = set(re.findall(r'\b\w{4,}\b', topic_lower))  # Words with 4+ chars

    # Expand topic words with related terms (e.g., "space" → includes "mars", "moon")
    topic_words = expand_topic_words(topic_words)

    matches = {}  # Use dict to deduplicate by ID

    # First, search hand-curated list (has better keywords)
    for pub in VERIFIED_PUBLICATIONS:
        total_score, breakdown = score_publication(pub, topic_lower, topic_words)
        if breakdown['keyword'] > 0:
            pub_id = pub["id"]
            total_score += 5  # Bonus for curated entries
            if pub_id not in matches or matches[pub_id][0] < total_score:
                matches[pub_id] = (total_score, pub, breakdown)

    # Then search scraped catalog (has broader coverage with enriched data)
    for pub in SCRAPED_CATALOG:
        total_score, breakdown = score_publication(pub, topic_lower, topic_words)
        # Allow match if good keyword score, or strong title match, or description match
        if breakdown['keyword'] > 0 or breakdown['title'] >= 3 or breakdown['description'] >= 1:
            pub_id = pub["id"]
            if pub_id not in matches or matches[pub_id][0] < total_score:
                matches[pub_id] = (total_score, pub, breakdown)

    # Sort by score (descending)
    sorted_matches = sorted(matches.values(), key=lambda x: -x[0])
    result = [m[1] for m in sorted_matches[:8]]  # Return up to 8 candidates

    # LLM fallback: only if we found very few/weak matches AND it's enabled
    # With enriched catalog data, we need LLM fallback less often
    # Threshold raised: need < 2 results with best score < 6 (was 4)
    weak_matches = len(result) < 2 or (sorted_matches and sorted_matches[0][0] < 6)
    if use_llm_fallback and weak_matches:
        # Gather candidate titles from catalog for LLM to evaluate
        # Filter to recent publications (higher IDs = more recent) and relevant topics
        candidate_pubs = []
        topic_categories = []

        # Map topic words to broad categories
        if any(w in topic_lower for w in ['ai', 'artificial', 'intelligence', 'machine', 'learning', 'robot']):
            topic_categories.extend(['technology', 'computing', 'artificial-intelligence'])
        if any(w in topic_lower for w in ['climate', 'warming', 'carbon', 'emissions', 'environment']):
            topic_categories.extend(['climate', 'environment', 'energy'])
        if any(w in topic_lower for w in ['cancer', 'tumor', 'oncology', 'immunotherapy']):
            topic_categories.extend(['cancer', 'biomedical', 'health'])
        if any(w in topic_lower for w in ['gene', 'genetic', 'dna', 'crispr', 'genome']):
            topic_categories.extend(['biomedical', 'genetics'])
        if any(w in topic_lower for w in ['vaccine', 'virus', 'infectious', 'pandemic', 'outbreak']):
            topic_categories.extend(['covid', 'global-health', 'infectious-disease'])
        if any(w in topic_lower for w in ['brain', 'neuro', 'mental', 'dementia', 'alzheimer']):
            topic_categories.extend(['mental-health', 'behavioral-health', 'neuroscience'])
        if any(w in topic_lower for w in ['space', 'nasa', 'planet', 'asteroid', 'mars', 'moon']):
            topic_categories.extend(['astronomy', 'space', 'planetary'])
        if any(w in topic_lower for w in ['ocean', 'marine', 'sea', 'coastal', 'fish']):
            topic_categories.extend(['ocean', 'environment', 'marine'])

        # Get recent publications (last 400 by ID) that might match
        recent_pubs = sorted(SCRAPED_CATALOG, key=lambda x: int(x.get('id', 0)), reverse=True)[:400]

        for pub in recent_pubs:
            pub_topics = pub.get('topics', [])
            # Include if matches a category or has a matching title word
            if any(cat in pub_topics for cat in topic_categories):
                candidate_pubs.append(pub)
            elif any(word in pub.get('title', '').lower() for word in topic_words if len(word) >= 5):
                candidate_pubs.append(pub)

            if len(candidate_pubs) >= 20:
                break

        if candidate_pubs:
            titles = [p['title'] for p in candidate_pubs]
            llm_indices = llm_semantic_match(topic_name, titles)

            for idx in llm_indices:
                pub = candidate_pubs[idx]
                pub_id = pub['id']
                if pub_id not in matches:
                    # LLM match gets score 3 with breakdown indicating LLM source
                    llm_breakdown = {'keyword': 0, 'title': 0, 'description': 0, 'recency': 0, 'llm': 3}
                    matches[pub_id] = (3, pub, llm_breakdown)

            # Re-sort and return
            sorted_matches = sorted(matches.values(), key=lambda x: -x[0])
            result = [m[1] for m in sorted_matches[:8]]  # Return up to 8 candidates

    return result


def find_current_projects_for_topic(topic_name):
    """Find relevant current/in-progress NASEM projects for a topic."""
    topic_lower = topic_name.lower()
    topic_words = set(re.findall(r'\b\w{4,}\b', topic_lower))
    matches = []

    for project in CURRENT_PROJECTS:
        title_lower = project.get("title", "").lower()
        score = 0

        # Check word matches in title
        for word in topic_words:
            if re.search(r'\b' + re.escape(word) + r'\b', title_lower):
                score += 2

        if score >= 2:  # At least one significant word match
            matches.append((score, project))

    # Sort and return top matches
    matches.sort(key=lambda x: -x[0])
    return [m[1] for m in matches[:3]]  # Return up to 3 current projects


def match_topics_to_nasem(topics, use_llm_fallback=True):
    """Match topics to NASEM publications and current projects.

    Args:
        topics: List of topic dicts with 'topic' key
        use_llm_fallback: Whether to use LLM for weak matches (default True)
                          Set to False to minimize LLM costs
    """
    pub_count = len(SCRAPED_CATALOG) if SCRAPED_CATALOG else len(VERIFIED_PUBLICATIONS)
    proj_count = len(CURRENT_PROJECTS)

    # Check if catalog has enriched data
    enriched = any(p.get('description') or p.get('year') for p in SCRAPED_CATALOG[:10])
    enriched_status = "enriched" if enriched else "basic"

    print(f"Matching topics to NASEM ({pub_count} publications [{enriched_status}] + {proj_count} projects)...")
    if not use_llm_fallback:
        print("  (LLM fallback disabled - using algorithmic matching only)")
    print()

    for topic in topics:
        topic_name = re.sub(r"^TOPIC\s*\\d+:\\s*", "", topic.get("topic", "Unknown"))
        topic["topic"] = topic_name
        print(f"  Matching: {topic_name}")

        # Find matching publications
        candidates = find_publications_for_topic(topic_name, use_llm_fallback=use_llm_fallback)
        print(f"    Publications: {len(candidates)} found")

        verified = []
        for pub in candidates[:5]:  # Take top 5 matches
            url = f"https://nap.nationalacademies.org/catalog/{pub['id']}"
            print(f"      [PUB] {pub['title'][:50]}...")
            verified.append({
                "title": pub["title"],
                "url": url,
                "type": "publication",
                "snippet": ""
            })

        # Find matching current projects
        projects = find_current_projects_for_topic(topic_name)
        print(f"    Current Projects: {len(projects)} found")

        for proj in projects[:2]:  # Take top 2 projects
            print(f"      [PROJ] {proj['title'][:50]}...")
            verified.append({
                "title": proj["title"],
                "url": proj.get("url", ""),
                "type": "current_project",
                "snippet": f"Status: {proj.get('status', 'in_progress')}"
            })

        topic["nasem_matches"] = verified
        if verified:
            print(f"    [OK] Total {len(verified)} match(es)")
        else:
            print(f"    [!] No matches found")
        print()

    return topics


if __name__ == "__main__":
    print("Testing NASEM matcher with verified database...")
    print()
    print("=" * 60)

    # Test with various topics
    test_topics = [
        {"topic": "AI's Impact on Scientific Research", "summary": "AI transforming research"},
        {"topic": "Climate Change and Arctic Ecosystems", "summary": "Climate impacts"},
        {"topic": "Cancer and Immunotherapy Advances", "summary": "Cancer treatment"},
        {"topic": "Genetic Testing and Genomics", "summary": "Genetics research"},
        {"topic": "Evolution and Origins of Life", "summary": "Evolution studies"},
        {"topic": "Aging Population and Healthcare", "summary": "Aging society"},
    ]

    results = match_topics_to_nasem(test_topics)

    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    for t in results:
        print(f"\nTopic: {t['topic']}")
        matches = t.get("nasem_matches", [])
        if matches:
            for m in matches:
                print(f"  - {m['title']}")
                print(f"    {m['url']}")
        else:
            print("  (no matches)")

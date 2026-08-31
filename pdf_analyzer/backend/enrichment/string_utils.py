import re
import unicodedata
from typing import List, Dict, Any, Tuple
from difflib import SequenceMatcher

def normalize_string(text: str) -> str:
    """
    Normalize string:
    - Unicode decomposition (NFKD) stripping accents/diacritics
    - Lowercase
    - Strip punctuation
    - Normalize whitespace
    """
    if not text:
        return ""
    # Normalize unicode accents
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    # Remove et al.
    text = re.sub(r"\bet\s+al\.?\b", "", text)
    # Replace non-alphanumeric characters (except spaces) with space
    text = re.sub(r"[^\w\s]", " ", text)
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text

def calculate_string_similarity(str1: str, str2: str) -> float:
    """Calculate SequenceMatcher similarity ratio between two normalized strings."""
    norm1 = normalize_string(str1)
    norm2 = normalize_string(str2)
    if not norm1 and not norm2:
        return 1.0
    if not norm1 or not norm2:
        return 0.0
    if norm1 == norm2:
        return 1.0
    return SequenceMatcher(None, norm1, norm2).ratio()

def parse_author_name(name_str: str) -> Dict[str, str]:
    if not name_str:
        return {"name": "", "given": "", "family": ""}
        
    clean_name = re.sub(r"^(?:Dr\.|Prof\.|Eng\.|Mr\.|Ms\.|Mrs\.|Ph\.D\.)\s*", "", name_str.strip(), flags=re.IGNORECASE).strip()
    clean_name = re.sub(r"^[\d\*\†\‡\§\^,#\-]+|[\d\*\†\‡\§\^,#\-\.]+$", "", clean_name).strip()
    
    if not clean_name:
        fallback = name_str.strip()
        return {"name": fallback, "given": "", "family": fallback}
    
    if "," in clean_name:
        parts = [p.strip() for p in clean_name.split(",", 1)]
        family = parts[0] if parts else clean_name
        given = parts[1] if len(parts) > 1 else ""
        display_name = f"{given} {family}".strip() if given else family
    else:
        parts = clean_name.split()
        if not parts:
            family = clean_name
            given = ""
            display_name = clean_name
        elif len(parts) == 1:
            family = parts[0]
            given = ""
            display_name = family
        else:
            family = parts[-1]
            given = " ".join(parts[:-1])
            display_name = clean_name
            
    return {
        "name": display_name,
        "given": given,
        "family": family
    }

def match_authors(authors1: List[Any], authors2: List[Any]) -> float:
    """
    Calculate author overlap score between two author lists (0.0 to 1.0).
    authors1/authors2 can be lists of strings or author dicts (with 'name', 'family', 'given').
    """
    def extract_families(authors: List[Any]) -> List[Tuple[str, str]]:
        res = []
        for a in authors:
            if isinstance(a, dict):
                fam = normalize_string(a.get("family", "") or a.get("name", ""))
                giv = normalize_string(a.get("given", ""))
            else:
                parsed = parse_author_name(str(a))
                fam = normalize_string(parsed["family"])
                giv = normalize_string(parsed["given"])
            if fam:
                res.append((fam, giv))
        return res

    list1 = extract_families(authors1)
    list2 = extract_families(authors2)

    if not list1 or not list2:
        return 0.0

    matched_count = 0
    for fam1, giv1 in list1:
        for fam2, giv2 in list2:
            # Check family name match or sub-match
            if fam1 == fam2 or (len(fam1) > 3 and fam1 in fam2) or (len(fam2) > 3 and fam2 in fam1):
                # Family matches; check given name/initials if available
                if giv1 and giv2:
                    if giv1[0] == giv2[0]:
                        matched_count += 1
                        break
                else:
                    matched_count += 1
                    break

    max_len = max(len(list1), len(list2))
    min_len = min(len(list1), len(list2))
    
    # Overlap relative to the smaller list, penalized slightly by length mismatch
    overlap = matched_count / float(min_len) if min_len > 0 else 0.0
    len_penalty = min_len / float(max_len) if max_len > 0 else 1.0
    
    return round(overlap * (0.8 + 0.2 * len_penalty), 2)

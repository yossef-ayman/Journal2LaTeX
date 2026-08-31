from typing import Dict, List, Any, Optional, Tuple
from enrichment.parser import ParsedReference
from enrichment.string_utils import (
    normalize_string,
    calculate_string_similarity,
    match_authors
)
from enrichment.config import config


class ReferenceMatcher:
    """
    Evaluates candidate works from academic providers (OpenAlex, Crossref, Google Scholar)
    against a parsed reference, computing field-level similarity scores and a calibrated
    confidence score (0.0 to 1.0) with robust status classification:
      - 'matched'        (confidence >= 0.80)
      - 'low_confidence' (0.50 <= confidence < 0.80)
      - 'not_found'      (confidence < 0.50)
    """

    @staticmethod
    def calculate_confidence(
        parsed_ref: ParsedReference, candidate: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate overall confidence score (0.0 to 1.0) and component scores
        between a parsed reference and a candidate work dict.
        """
        scores: Dict[str, float] = {
            "doi_match": 0.0,
            "title_sim": 0.0,
            "author_sim": 0.0,
            "year_match": 0.0,
            "journal_sim": 0.0,
            "year_diff": -1.0
        }

        cand_doi = (candidate.get("doi") or "").lower().strip()
        cand_title = candidate.get("title") or candidate.get("display_name") or ""
        cand_authors = candidate.get("authors") or []
        cand_year = candidate.get("year") or candidate.get("publication_year")
        cand_journal = candidate.get("journal") or candidate.get("venue") or ""

        # 1. DOI exact match check (Highest Confidence = 1.00)
        ref_doi = (parsed_ref.doi or "").lower().strip()
        cand_doi_clean = cand_doi.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
        ref_doi_clean = ref_doi.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()

        if ref_doi_clean and cand_doi_clean and ref_doi_clean == cand_doi_clean:
            scores["doi_match"] = 1.0
            scores["title_sim"] = calculate_string_similarity(parsed_ref.title or "", cand_title)
            scores["author_sim"] = match_authors(parsed_ref.authors or parsed_ref.raw_authors, cand_authors)
            scores["year_match"] = 1.0
            return 1.0, scores

        # 2. Check missing / too short title
        ref_title_clean = normalize_string(parsed_ref.title)
        if not ref_title_clean or len(ref_title_clean) < 4:
            scores["title_sim"] = 0.0
            return 0.20, scores

        # 3. Title similarity & Author overlap
        scores["title_sim"] = calculate_string_similarity(parsed_ref.title, cand_title)
        scores["author_sim"] = match_authors(parsed_ref.authors or parsed_ref.raw_authors, cand_authors)

        # 4. Publication year match
        if parsed_ref.year and cand_year:
            try:
                year_diff = abs(int(parsed_ref.year) - int(cand_year))
                scores["year_diff"] = float(year_diff)
                if year_diff == 0:
                    scores["year_match"] = 1.0
                elif year_diff == 1:
                    scores["year_match"] = 0.8
                elif year_diff == 2:
                    scores["year_match"] = 0.5
                else:
                    scores["year_match"] = 0.0
            except (ValueError, TypeError):
                scores["year_match"] = 0.5
        else:
            scores["year_match"] = 0.5

        # 5. Journal / Venue similarity
        if parsed_ref.journal and cand_journal:
            scores["journal_sim"] = calculate_string_similarity(parsed_ref.journal, cand_journal)
        else:
            scores["journal_sim"] = 0.5

        # ─────────────────────────────────────────────────────────────────
        # Matching Strategy Hierarchy:
        # ─────────────────────────────────────────────────────────────────
        t_sim = scores["title_sim"]
        a_sim = scores["author_sim"]
        y_diff = scores["year_diff"]

        # Case 1: Very Strong Title Match (>= 0.90) + Author Overlap (>= 0.25)
        # Expected confidence: 0.92 - 0.99
        if t_sim >= 0.90 and a_sim >= 0.25:
            confidence = 0.90 + 0.08 * t_sim + 0.02 * a_sim

        # Case 2: Exact/Very Strong Title Match (>= 0.92) without parsed author conflicts
        elif t_sim >= 0.92 and (y_diff < 0 or y_diff <= 2):
            confidence = 0.90 + 0.08 * t_sim

        # Case 3: Strong Title Match (>= 0.80) with moderate author or year agreement
        # Expected confidence: 0.80 - 0.89
        elif t_sim >= 0.80 and (a_sim >= 0.20 or y_diff == 0 or y_diff == 1 or not parsed_ref.authors):
            confidence = 0.80 + 0.10 * t_sim + 0.05 * a_sim

        # Case 4: Moderate Title Match (>= 0.65) with Author or Year agreement
        # Expected confidence: 0.65 - 0.79
        elif t_sim >= 0.65 and (a_sim >= 0.30 or (y_diff >= 0 and y_diff <= 1)):
            confidence = 0.65 + 0.12 * t_sim + 0.10 * a_sim

        # Case 5: Moderate Title only (0.50 <= t_sim < 0.65)
        # Expected confidence: 0.50 - 0.64
        elif t_sim >= 0.50:
            raw_conf = 0.50 + 0.20 * (t_sim - 0.50) + 0.15 * a_sim
            if a_sim < 0.15 and y_diff > 2:
                raw_conf *= 0.70
            confidence = raw_conf

        # Case 6: Weak match below 0.50
        else:
            confidence = 0.40 * t_sim + 0.35 * a_sim + 0.15 * scores["year_match"] + 0.10 * scores["journal_sim"]

        confidence = min(1.0, max(0.0, round(confidence, 2)))
        return confidence, scores

    @classmethod
    def match_candidate(
        cls,
        parsed_ref: ParsedReference,
        candidates: List[Dict[str, Any]],
        threshold: Optional[float] = None
    ) -> Tuple[Optional[Dict[str, Any]], float, str]:
        """
        Evaluate candidate works against parsed reference and return:
        (best_candidate, best_confidence, match_status)
        where match_status is 'matched' (>= threshold), 'low_confidence' (>= 0.50), or 'not_found' (< 0.50).
        """
        if threshold is None:
            threshold = config.match_threshold

        if not candidates:
            return None, 0.0, "not_found"

        best_cand = None
        best_conf = -1.0

        for cand in candidates:
            conf, _ = cls.calculate_confidence(parsed_ref, cand)
            if conf > best_conf:
                best_conf = conf
                best_cand = cand

        if not best_cand or best_conf < 0.50:
            return None, max(0.0, best_conf), "not_found"

        if best_conf >= threshold:
            status = "matched"
        else:
            status = "low_confidence"

        return best_cand, best_conf, status

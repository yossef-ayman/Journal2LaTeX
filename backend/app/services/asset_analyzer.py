import json
from pathlib import Path
from typing import Any, Dict, List
from app.models.document import DocumentModel, BlockType
from app.utils.logger import get_job_logger


class AssetAnalyzer:
    """Service to classify document assets and maintain detailed traceability mappings."""

    def analyze_assets(self, job_id: str, doc_model: DocumentModel, temp_folder: Path) -> List[Dict[str, Any]]:
        """Classify extracted assets and store mappings with detailed surrounding context.

        Args:
            job_id: The job ID.
            doc_model: The extracted DocumentModel.
            temp_folder: The job's temporary workspace directory.

        Returns:
            A list of classified asset dictionaries.
        """
        logger = get_job_logger(job_id, "system")
        logger.info("Starting extended asset analysis for job: %s", job_id)

        media_dir = temp_folder / "intermediate" / "media"
        assets_list = []
        mapping_dict = {}

        # Default classification when no files exist
        if not media_dir.exists() or not media_dir.is_dir():
            logger.info("No media directory found. Skipping asset analysis.")
            self._save_reports(temp_folder, assets_list, mapping_dict)
            return assets_list

        # Gather figure blocks and biography details for image matching.
        # Each block is recorded with the section it actually belongs to.
        # Previously the map was built from a bare ``section`` left over from
        # the loop above, so every asset in the document reported the *last*
        # section as its source -- which made the traceability report say
        # nothing useful about where anything came from.
        all_blocks = []
        for section in doc_model.sections:
            for block in section.blocks:
                all_blocks.append((block, section.title))

        figure_blocks_map = {}
        equation_image_names = set()
        for idx, (block, section_title) in enumerate(all_blocks):
            if block.type == BlockType.FIGURE:
                path = block.content.get("path", "")
                caption = block.content.get("caption", "")

                # An equation that was pasted into Word as a picture is an
                # equation, not a figure.  The analyzer marks it when it reads
                # the DOCX; carrying that through here is what keeps it out of
                # figure numbering and out of the List of Figures.
                if block.content.get("is_equation"):
                    equation_image_names.add(Path(path).name)
                    continue

                # Extract surrounding paragraphs
                surrounding = []
                for i in range(idx - 1, -1, -1):
                    if all_blocks[i][0].type == BlockType.PARAGRAPH:
                        surrounding.append(all_blocks[i][0].content.get("text", ""))
                        break
                for i in range(idx + 1, len(all_blocks)):
                    if all_blocks[i][0].type == BlockType.PARAGRAPH:
                        surrounding.append(all_blocks[i][0].content.get("text", ""))
                        break

                figure_blocks_map[Path(path).name] = {
                    "caption": caption,
                    "surrounding": surrounding,
                    "original_path": path,
                    "source_block": f"section_{section_title}_block_{idx}"
                }

        author_names = [a.name.lower() for a in doc_model.authors]

        # Scan media files
        for asset_idx, item in enumerate(sorted(media_dir.iterdir())):
            if item.is_dir() or item.name.startswith("."):
                continue

            filename_lower = item.name.lower()
            asset_type = "unknown"
            associated_author = None
            caption = ""
            surrounding_paragraphs = []
            nearby_captions = []
            source_block = "metadata"

            # Check if this image belongs to an author biography
            # (docx biography image is often extracted in order or matching author name)
            is_bio_img = False
            for bio in doc_model.author_biographies:
                if bio.image_path and item.name in bio.image_path:
                    is_bio_img = True
                    associated_author = bio.author_name
                    # Update bio path with rendered media path
                    bio.image_path = f"media/{item.name}"
                    break

            # If not mapped by explicit path, search by author name matching
            if not is_bio_img:
                for author in doc_model.authors:
                    if author.name.lower() in filename_lower:
                        is_bio_img = True
                        associated_author = author.name
                        author.photo_path = f"media/{item.name}"
                        break

            # Populate block mapping
            block_info = figure_blocks_map.get(item.name)
            if block_info:
                asset_type = "figure"
                caption = block_info["caption"]
                surrounding_paragraphs = block_info["surrounding"]
                source_block = block_info["source_block"]
                if caption:
                    nearby_captions.append(caption)

            # An equation image, identified from the document model rather
            # than from its name.
            if item.name in equation_image_names:
                asset_type = "equation_image"
                source_block = "equation"

            # Structural evidence -- this file is the photograph named by a
            # biography entry, or by an author record -- outranks everything
            # below, because it says what the document itself does with the
            # file rather than what somebody called it.
            if is_bio_img:
                asset_type = "author_photo"
                source_block = f"biography_{associated_author}"

            # A filename keyword is the weakest possible evidence and is used
            # only when the document model said nothing at all: a manuscript
            # figure legitimately called "logo_comparison.png" is a figure, and
            # classifying it as template furniture would drop it from the
            # figure numbering.
            elif asset_type == "unknown" and "logo" in filename_lower:
                asset_type = "logo"
                source_block = "logo_block"

            if asset_type == "unknown":
                asset_type = "figure"

            asset_path = f"media/{item.name}"
            relationship_id = f"rId_asset_{asset_idx + 1}"
            
            asset_info = {
                "asset_index": asset_idx,
                "path": asset_path,
                "type": asset_type,
                "original_relationship_id": relationship_id,
                "surrounding_paragraphs": surrounding_paragraphs,
                "nearby_captions": nearby_captions
            }
            if caption:
                asset_info["caption"] = caption
            if associated_author:
                asset_info["author"] = associated_author

            assets_list.append(asset_info)

            original_path = block_info["original_path"] if block_info else item.name
            
            # Map values according to user requirements format
            mapping_dict[item.name] = {
                "original_asset": original_path,
                "rendered_asset": asset_path,
                "asset_type": asset_type,
                "source_block": source_block,
                "relationship_id": relationship_id,
                "order": asset_idx
            }

        # Write reports
        self._save_reports(temp_folder, assets_list, mapping_dict)
        logger.info("Extended asset classification completed. Assets classified: %d", len(assets_list))
        return assets_list

    def _save_reports(self, temp_folder: Path, assets_list: List[dict], mapping_dict: dict) -> None:
        """Write assets.json and asset_mapping.json to intermediate folder."""
        intermediate_dir = temp_folder / "intermediate"
        intermediate_dir.mkdir(parents=True, exist_ok=True)

        assets_path = intermediate_dir / "assets.json"
        assets_path.write_text(json.dumps({"assets": assets_list}, indent=2), encoding="utf-8")

        mapping_path = intermediate_dir / "asset_mapping.json"
        mapping_path.write_text(json.dumps({"mappings": mapping_dict}, indent=2), encoding="utf-8")

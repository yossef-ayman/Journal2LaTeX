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

        # Gather figure blocks and biography details for image matching
        all_blocks = []
        for section in doc_model.sections:
            for block in section.blocks:
                all_blocks.append(block)

        figure_blocks_map = {}
        for idx, block in enumerate(all_blocks):
            if block.type == BlockType.FIGURE:
                path = block.content.get("path", "")
                caption = block.content.get("caption", "")
                
                # Extract surrounding paragraphs
                surrounding = []
                for i in range(idx - 1, -1, -1):
                    if all_blocks[i].type == BlockType.PARAGRAPH:
                        surrounding.append(all_blocks[i].content.get("text", ""))
                        break
                for i in range(idx + 1, len(all_blocks)):
                    if all_blocks[i].type == BlockType.PARAGRAPH:
                        surrounding.append(all_blocks[i].content.get("text", ""))
                        break

                figure_blocks_map[Path(path).name] = {
                    "caption": caption,
                    "surrounding": surrounding,
                    "original_path": path,
                    "source_block": f"section_{section.title}_block_{idx}"
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

            if is_bio_img:
                asset_type = "author_photo"
                source_block = f"biography_{associated_author}"

            if "logo" in filename_lower:
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

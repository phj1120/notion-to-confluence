"""Converter for transforming Notion blocks to Confluence Storage Format."""

from typing import List, Dict, Any, Callable
import html

from src.core.logger import get_logger
from src.core.exceptions import ConversionError

logger = get_logger()


class NotionToConfluenceConverter:
    """Convert Notion blocks to Confluence Storage Format.

    This class handles the transformation of various Notion block types
    into Confluence's storage format (HTML-based markup).
    """

    # Mapping of Notion block types to converter methods
    BLOCK_TYPE_HANDLERS: Dict[str, str] = {
        "paragraph": "convert_paragraph",
        "heading_1": "convert_heading_1",
        "heading_2": "convert_heading_2",
        "heading_3": "convert_heading_3",
        "bulleted_list_item": "convert_bulleted_list_item",
        "numbered_list_item": "convert_numbered_list_item",
        "code": "convert_code",
        "quote": "convert_quote",
        "divider": "convert_divider",
        "table": "convert_table",
        "callout": "convert_callout",
        "toggle": "convert_toggle",
        "to_do": "convert_to_do",
        "image": "convert_image",
        "column_list": "convert_column_list",
        "column": "convert_column",
    }

    def __init__(self, confluence_client=None, page_id=None):
        """Initialize the converter.

        Args:
            confluence_client: Optional Confluence client for image uploads
            page_id: Optional Confluence page ID for image attachments
        """
        self.confluence_client = confluence_client
        self.page_id = page_id
        self.uploaded_images = {}  # Cache of uploaded images: notion_url -> confluence_filename

    def convert_blocks(self, blocks: List[Dict[str, Any]]) -> str:
        """Convert a list of Notion blocks to Confluence storage format.

        Args:
            blocks: List of Notion block dictionaries

        Returns:
            HTML string in Confluence storage format
        """
        html_parts = []
        for block in blocks:
            try:
                converted = self.convert_block(block)
                if converted:
                    html_parts.append(converted)
            except Exception as e:
                block_id = block.get("id", "unknown")
                block_type = block.get("type", "unknown")
                logger.error(
                    f"Failed to convert block {block_id} (type: {block_type}): {e}"
                )
                # Continue with next block instead of failing completely

        return "".join(html_parts)

    def convert_block(self, block: Dict[str, Any]) -> str:
        """Convert a single Notion block to Confluence HTML.

        Args:
            block: Notion block dictionary

        Returns:
            HTML string in Confluence storage format

        Raises:
            ConversionError: If block conversion fails
        """
        block_type = block.get("type")

        if not block_type:
            logger.warning(f"Block without type: {block.get('id')}")
            return ""

        # Check if we have a handler for this block type
        handler_name = self.BLOCK_TYPE_HANDLERS.get(block_type)
        if handler_name:
            converter_method = getattr(self, handler_name)
            return converter_method(block)
        else:
            logger.warning(f"Unsupported block type: {block_type}")
            return ""

    def convert_paragraph(self, block: Dict[str, Any]) -> str:
        """Convert paragraph block."""
        text = self.extract_rich_text(block["paragraph"].get("rich_text", []))
        if not text:
            return "<p></p>"
        return f"<p>{text}</p>"

    def convert_heading_1(self, block: Dict[str, Any]) -> str:
        """Convert heading 1 block."""
        text = self.extract_rich_text(block["heading_1"].get("rich_text", []))
        return f"<h1>{text}</h1>"

    def convert_heading_2(self, block: Dict[str, Any]) -> str:
        """Convert heading 2 block."""
        text = self.extract_rich_text(block["heading_2"].get("rich_text", []))
        return f"<h2>{text}</h2>"

    def convert_heading_3(self, block: Dict[str, Any]) -> str:
        """Convert heading 3 block."""
        text = self.extract_rich_text(block["heading_3"].get("rich_text", []))
        return f"<h3>{text}</h3>"

    def convert_bulleted_list_item(self, block: Dict[str, Any]) -> str:
        """Convert bulleted list item."""
        text = self.extract_rich_text(block["bulleted_list_item"].get("rich_text", []))
        children_html = ""
        if block.get("children"):
            children_html = self.convert_blocks(block["children"])

        return f"<ul><li>{text}{children_html}</li></ul>"

    def convert_numbered_list_item(self, block: Dict[str, Any]) -> str:
        """Convert numbered list item."""
        text = self.extract_rich_text(block["numbered_list_item"].get("rich_text", []))
        children_html = ""
        if block.get("children"):
            children_html = self.convert_blocks(block["children"])

        return f"<ol><li>{text}{children_html}</li></ol>"

    def convert_code(self, block: Dict[str, Any]) -> str:
        """Convert code block."""
        code_data = block.get("code", {})
        text = self.extract_rich_text(code_data.get("rich_text", []), preserve_formatting=False)
        language = code_data.get("language", "plain text")

        escaped_code = html.escape(text)
        return f'<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">{language}</ac:parameter><ac:plain-text-body><![CDATA[{escaped_code}]]></ac:plain-text-body></ac:structured-macro>'

    def convert_quote(self, block: Dict[str, Any]) -> str:
        """Convert quote block."""
        text = self.extract_rich_text(block["quote"].get("rich_text", []))
        return f"<blockquote><p>{text}</p></blockquote>"

    def convert_divider(self, block: Dict[str, Any]) -> str:
        """Convert divider block."""
        return "<hr />"

    def convert_table(self, block: Dict[str, Any]) -> str:
        """Convert table block."""
        table_data = block.get("table", {})
        has_column_header = table_data.get("has_column_header", False)
        has_row_header = table_data.get("has_row_header", False)

        children = block.get("children", [])
        if not children:
            return ""

        html_parts = ["<table><tbody>"]

        for idx, row_block in enumerate(children):
            if row_block.get("type") != "table_row":
                continue

            cells = row_block.get("table_row", {}).get("cells", [])
            is_header_row = has_column_header and idx == 0

            html_parts.append("<tr>")
            for cell_idx, cell in enumerate(cells):
                cell_text = self.extract_rich_text(cell)
                is_header_cell = is_header_row or (has_row_header and cell_idx == 0)
                tag = "th" if is_header_cell else "td"
                html_parts.append(f"<{tag}>{cell_text}</{tag}>")
            html_parts.append("</tr>")

        html_parts.append("</tbody></table>")
        return "".join(html_parts)

    def convert_callout(self, block: Dict[str, Any]) -> str:
        """Convert callout block to info panel."""
        text = self.extract_rich_text(block["callout"].get("rich_text", []))

        # Process children blocks if they exist (for multi-line callouts)
        children_html = ""
        if block.get("children"):
            children_html = self.convert_blocks(block["children"])

        # Combine the callout text and children
        content = f"<p>{text}</p>{children_html}" if text else children_html

        return f'<ac:structured-macro ac:name="info"><ac:rich-text-body>{content}</ac:rich-text-body></ac:structured-macro>'

    def convert_toggle(self, block: Dict[str, Any]) -> str:
        """Convert toggle block to expand macro."""
        text = self.extract_rich_text(block["toggle"].get("rich_text", []))
        children_html = ""
        if block.get("children"):
            children_html = self.convert_blocks(block["children"])

        return f'<ac:structured-macro ac:name="expand"><ac:parameter ac:name="title">{text}</ac:parameter><ac:rich-text-body>{children_html}</ac:rich-text-body></ac:structured-macro>'

    def convert_to_do(self, block: Dict[str, Any]) -> str:
        """Convert to-do block to task list."""
        todo_data = block.get("to_do", {})
        text = self.extract_rich_text(todo_data.get("rich_text", []))
        checked = todo_data.get("checked", False)

        status = "complete" if checked else "incomplete"
        return f'<ac:task><ac:task-id>{block["id"]}</ac:task-id><ac:task-status>{status}</ac:task-status><ac:task-body>{text}</ac:task-body></ac:task>'

    def convert_image(self, block: Dict[str, Any]) -> str:
        """Convert image block to Confluence image.

        Downloads the image from Notion and uploads to Confluence as attachment,
        then returns the Confluence image reference.
        """
        image_data = block.get("image", {})
        image_type = image_data.get("type")

        # Get image URL based on type
        image_url = None
        if image_type == "external":
            image_url = image_data.get("external", {}).get("url")
        elif image_type == "file":
            image_url = image_data.get("file", {}).get("url")
        elif image_type == "file_upload":
            logger.warning(f"file_upload type not yet supported for image blocks")
            return ""

        if not image_url:
            logger.warning(f"No URL found for image block {block.get('id')}")
            return ""

        # If no Confluence client available, return placeholder comment
        if not self.confluence_client or not self.page_id:
            logger.warning("Image support requires Confluence client and page ID. Skipping image.")
            return f"<!-- Image: {image_url} -->"

        # Check if already uploaded
        if image_url in self.uploaded_images:
            filename = self.uploaded_images[image_url]
            logger.debug(f"Using cached image: {filename}")
            return f'<ac:image><ri:attachment ri:filename="{html.escape(filename)}" /></ac:image>'

        # Download and upload the image
        try:
            import requests
            from pathlib import Path
            import hashlib

            # Download image
            logger.info(f"Downloading image from: {image_url}")
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()

            # Generate filename from URL or use hash
            url_path = Path(image_url.split("?")[0])  # Remove query params
            extension = url_path.suffix if url_path.suffix else ".png"
            # Use hash of URL to avoid filename conflicts
            url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
            filename = f"image_{url_hash}{extension}"

            # Upload to Confluence
            logger.info(f"Uploading image to Confluence: {filename}")
            self.confluence_client.upload_attachment(
                page_id=self.page_id,
                filename=filename,
                file_data=response.content,
                content_type=response.headers.get("content-type", "image/png")
            )

            # Cache the upload
            self.uploaded_images[image_url] = filename

            # Return Confluence image reference
            return f'<ac:image><ri:attachment ri:filename="{html.escape(filename)}" /></ac:image>'

        except Exception as e:
            logger.error(f"Failed to process image {image_url}: {e}")
            return f"<!-- Failed to load image: {image_url} -->"

    def convert_column_list(self, block: Dict[str, Any]) -> str:
        """Convert column_list block to Confluence table.

        Column lists in Notion are rendered as tables in Confluence,
        with each column becoming a table cell.
        """
        children = block.get("children", [])
        if not children:
            return ""

        # Filter only column blocks
        columns = [child for child in children if child.get("type") == "column"]
        if not columns:
            return ""

        # Build table with one row containing all columns
        html_parts = ["<table><tbody><tr>"]

        for column in columns:
            # Process each column's content
            column_content = ""
            if column.get("children"):
                column_content = self.convert_blocks(column["children"])

            html_parts.append(f"<td>{column_content}</td>")

        html_parts.append("</tr></tbody></table>")
        return "".join(html_parts)

    def convert_column(self, block: Dict[str, Any]) -> str:
        """Convert individual column block.

        Columns are handled by column_list, so this should not be called directly.
        """
        logger.warning("Column block should be handled by column_list parent")
        if block.get("children"):
            return self.convert_blocks(block["children"])
        return ""

    def extract_rich_text(self, rich_text_array: List[Dict[str, Any]], preserve_formatting: bool = True) -> str:
        """Extract and format rich text from Notion.

        Converts Notion rich text to Confluence-compatible HTML.
        Uses Confluence Storage Format tags: <strong>, <em>, <s>, <u>, <code>
        """
        if not rich_text_array:
            return ""

        result_parts = []
        for text_obj in rich_text_array:
            text = text_obj.get("plain_text", "")

            if not preserve_formatting:
                result_parts.append(html.escape(text))
                continue

            # Escape HTML special characters first
            text = html.escape(text)

            # Convert newlines to <br /> tags for line breaks
            text = text.replace("\n", "<br />")

            # Note: Inline formatting (bold, italic, etc.) causes XhtmlException errors
            # in some Confluence Cloud instances. Keeping formatting disabled for stability.
            # Text will be migrated without formatting but with preserved structure and images.

            # Handle links (wrap everything if it's a link)
            if text_obj.get("href"):
                href = html.escape(text_obj["href"])
                text = f'<a href="{href}">{text}</a>'

            result_parts.append(text)

        return "".join(result_parts)

"""PDF processing MCP server: extract, convert, manipulate, generate."""
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from mcp_arena.mcp.server import BaseMCPServer

try:
    import fitz as _fitz_lib
except ImportError:
    _fitz_lib = None

try:
    from PyPDF2 import PdfReader as _PdfReader, PdfWriter as _PdfWriter
except ImportError:
    _PdfReader = _PdfWriter = None

try:
    from reportlab.pdfgen import canvas as _rl_canvas
    from reportlab.lib.pagesizes import letter as _rl_letter, A4 as _rl_A4
    from reportlab.lib.styles import getSampleStyleSheet as _rl_get_styles
    from reportlab.platypus import (
        SimpleDocTemplate as _rl_doc, Paragraph as _rl_para, Spacer as _rl_spacer
    )
    from reportlab.lib.units import inch as _rl_inch
except ImportError:
    _rl_canvas = _rl_letter = _rl_A4 = _rl_get_styles = None
    _rl_doc = _rl_para = _rl_spacer = _rl_inch = None

try:
    import pdfplumber as _pdfplumber_lib
except ImportError:
    _pdfplumber_lib = None


def _ensure_fitz():
    if _fitz_lib is None:
        raise ImportError("PyMuPDF is required. pip install PyMuPDF")
    return _fitz_lib


def _ensure_pypdf2():
    if _PdfReader is None:
        raise ImportError("PyPDF2 is required. pip install PyPDF2")
    return _PdfReader, _PdfWriter


def _ensure_reportlab():
    if _rl_doc is None:
        raise ImportError("reportlab is required. pip install reportlab")
    return {
        "canvas": _rl_canvas,
        "pagesizes": {"letter": _rl_letter, "A4": _rl_A4},
        "styles": _rl_get_styles,
        "doc": _rl_doc,
        "para": _rl_para,
        "spacer": _rl_spacer,
        "inch": _rl_inch,
    }


def _ensure_pdfplumber():
    if _pdfplumber_lib is None:
        raise ImportError("pdfplumber is required. pip install pdfplumber")
    return _pdfplumber_lib


class PDFMCPServer(BaseMCPServer):
    """PDF processing MCP server (PyMuPDF, PyPDF2, ReportLab)."""
    _REQUIRED_EXTRAS = {"PyPDF2": "pdf", "fitz": "pdf", "pdfplumber": "pdf", "reportlab": "pdf"}

    def __init__(
        self,
        default_output_dir: Optional[str] = None,
        image_quality: int = 90,
        image_format: str = "png",
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs,
    ):
        self.default_output_dir = default_output_dir or os.path.join(os.getcwd(), "pdf_output")
        self.image_quality = image_quality
        self.image_format = image_format
        Path(self.default_output_dir).mkdir(parents=True, exist_ok=True)

        super().__init__(
            name="PDF Processing MCP Server",
            description="MCP server for advanced PDF manipulation, extraction, conversion, and generation",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )

    def _register_tools(self) -> None:
        """Register all PDF processing tools."""
        self._register_info_tools()
        self._register_extraction_tools()
        self._register_conversion_tools()
        self._register_manipulation_tools()
        self._register_generation_tools()
        self._register_advanced_tools()

    def _register_info_tools(self):
        """Register PDF information tools."""

        @self.mcp_server.tool()
        def get_pdf_info(pdf_path: str) -> Dict[str, Any]:
            """Get detailed information about a PDF file.

            Args:
                pdf_path: Path to the PDF file
            """
            try:
                fitz = _ensure_fitz()

                with fitz.open(pdf_path) as doc:
                    metadata = doc.metadata
                    info = {
                        "path": pdf_path,
                        "filename": os.path.basename(pdf_path),
                        "pages": len(doc),
                        "version": str(doc.version),
                        "encrypted": doc.is_encrypted,
                        "size_bytes": os.path.getsize(pdf_path),
                        "title": metadata.get("title"),
                        "author": metadata.get("author"),
                        "creator": metadata.get("creator"),
                        "producer": metadata.get("producer"),
                        "creation_date": metadata.get("creationDate"),
                        "modification_date": metadata.get("modDate"),
                    }
                return {"success": True, "info": info}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def check_pdf_accessibility(pdf_path: str) -> Dict[str, Any]:
            """Check PDF accessibility features."""
            try:
                fitz = _ensure_fitz()

                with fitz.open(pdf_path) as doc:
                    # Check basic accessibility features
                    has_bookmarks = len(doc.get_toc()) > 0
                    has_metadata = bool(doc.metadata)

                    # Check if text is extractable (not scanned)
                    first_page = doc[0]
                    text = first_page.get_text()
                    has_text = len(text.strip()) > 100  # Arbitrary threshold

                    # Check for tags (structured PDF)
                    is_tagged = doc.is_form_pdf

                return {
                    "success": True,
                    "has_bookmarks": has_bookmarks,
                    "has_metadata": has_metadata,
                    "has_extractable_text": has_text,
                    "is_tagged": is_tagged,
                    "is_encrypted": doc.is_encrypted
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_extraction_tools(self):
        """Register PDF extraction tools."""

        @self.mcp_server.tool()
        def extract_text(
            pdf_path: str,
            pages: Optional[List[int]] = None,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Extract text from PDF.

            Args:
                pdf_path: Path to PDF file
                pages: List of page numbers to extract (1-indexed)
                output_path: Output text file path
            """
            try:
                fitz = _ensure_fitz()

                with fitz.open(pdf_path) as doc:
                    extracted_text = []

                    target_pages = pages if pages else range(len(doc))

                    for page_num in target_pages:
                        if 1 <= page_num <= len(doc):
                            page = doc[page_num - 1]
                            text = page.get_text()
                            extracted_text.append(f"--- Page {page_num} ---\n{text}\n")

                    full_text = "\n".join(extracted_text)

                    if output_path is None:
                        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
                        output_path = os.path.join(self.default_output_dir, f"{base_name}_text.txt")

                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(full_text)

                return {
                    "success": True,
                    "output_path": output_path,
                    "pages_extracted": len(extracted_text),
                    "text_length": len(full_text)
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def extract_text_by_page(
            pdf_path: str,
            page_number: int
        ) -> Dict[str, Any]:
            """Extract text from specific page."""
            try:
                fitz = _ensure_fitz()

                with fitz.open(pdf_path) as doc:
                    if page_number < 1 or page_number > len(doc):
                        return {"error": f"Page {page_number} not found. Document has {len(doc)} pages."}

                    page = doc[page_number - 1]
                    text = page.get_text()

                    return {
                        "success": True,
                        "page_number": page_number,
                        "text": text,
                        "text_length": len(text)
                    }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def extract_images(
            pdf_path: str,
            pages: Optional[List[int]] = None,
            output_dir: Optional[str] = None
        ) -> Dict[str, Any]:
            """Extract images from PDF."""
            try:
                fitz = _ensure_fitz()

                if output_dir is None:
                    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
                    output_dir = os.path.join(self.default_output_dir, f"{base_name}_images")

                Path(output_dir).mkdir(parents=True, exist_ok=True)

                extracted_images = []

                with fitz.open(pdf_path) as doc:
                    target_pages = pages if pages else range(len(doc))

                    for page_num in target_pages:
                        if 1 <= page_num <= len(doc):
                            page = doc[page_num - 1]
                            image_list = page.get_images()

                            for img_index, img_info in enumerate(image_list):
                                xref = img_info[0]
                                base_image = doc.extract_image(xref)

                                if base_image:
                                    image_data = base_image["image"]
                                    image_ext = base_image["ext"]

                                    filename = f"page_{page_num}_img_{img_index + 1}.{image_ext}"
                                    output_path = os.path.join(output_dir, filename)

                                    with open(output_path, "wb") as f:
                                        f.write(image_data)

                                    extracted_images.append({
                                        "page": page_num,
                                        "image_index": img_index + 1,
                                        "filename": filename,
                                        "format": image_ext,
                                        "size_bytes": len(image_data)
                                    })

                return {
                    "success": True,
                    "output_dir": output_dir,
                    "images_extracted": len(extracted_images),
                    "images": extracted_images
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def extract_links(pdf_path: str) -> Dict[str, Any]:
            """Extract hyperlinks from PDF."""
            try:
                fitz = _ensure_fitz()

                links = []

                with fitz.open(pdf_path) as doc:
                    for page_num in range(len(doc)):
                        page = doc[page_num]
                        link_dicts = page.get_links()

                        for link_index, link_info in enumerate(link_dicts):
                            if 'uri' in link_info:
                                links.append({
                                    "page": page_num + 1,
                                    "link_index": link_index + 1,
                                    "uri": link_info['uri'],
                                    "link_type": link_info.get('kind', 'unknown')
                                })

                return {
                    "success": True,
                    "links_count": len(links),
                    "links": links
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def extract_tables(
            pdf_path: str,
            pages: Optional[List[int]] = None
        ) -> Dict[str, Any]:
            """Extract tables from PDF using pdfplumber."""
            try:
                pdfplumber = _ensure_pdfplumber()

                tables = []

                with pdfplumber.open(pdf_path) as pdf:
                    target_pages = pages if pages else range(len(pdf.pages))

                    for page_num in target_pages:
                        if 0 <= page_num < len(pdf.pages):
                            page = pdf.pages[page_num]
                            page_tables = page.extract_tables()

                            for table_index, table_data in enumerate(page_tables):
                                if table_data:
                                    tables.append({
                                        "page": page_num + 1,
                                        "table_index": table_index + 1,
                                        "rows": len(table_data),
                                        "columns": len(table_data[0]) if table_data else 0,
                                        "data": table_data
                                    })

                return {
                    "success": True,
                    "tables_count": len(tables),
                    "tables": tables
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_conversion_tools(self):
        """Register PDF conversion tools."""

        @self.mcp_server.tool()
        def convert_pdf_to_images(
            pdf_path: str,
            pages: Optional[List[int]] = None,
            output_dir: Optional[str] = None,
            dpi: int = 300,
            format: str = "png"
        ) -> Dict[str, Any]:
            """Convert PDF pages to images."""
            try:
                fitz = _ensure_fitz()

                if output_dir is None:
                    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
                    output_dir = os.path.join(self.default_output_dir, f"{base_name}_pages")

                Path(output_dir).mkdir(parents=True, exist_ok=True)

                converted_pages = []

                with fitz.open(pdf_path) as doc:
                    target_pages = pages if pages else range(len(doc))

                    for page_num in target_pages:
                        if 1 <= page_num <= len(doc):
                            page = doc[page_num - 1]

                            # Convert to image
                            mat = fitz.Matrix(dpi / 72, dpi / 72)
                            pix = page.get_pixmap(matrix=mat)

                            filename = f"page_{page_num}.{format}"
                            output_path = os.path.join(output_dir, filename)

                            if format == "png":
                                pix.save(output_path)
                            else:
                                pix.save(output_path, format)

                            converted_pages.append({
                                "page": page_num,
                                "filename": filename,
                                "width": pix.width,
                                "height": pix.height,
                                "size_bytes": os.path.getsize(output_path)
                            })

                return {
                    "success": True,
                    "output_dir": output_dir,
                    "pages_converted": len(converted_pages),
                    "dpi": dpi,
                    "format": format
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def convert_pdf_to_text(
            pdf_path: str,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Convert entire PDF to text file."""
            try:
                return self.extract_text(pdf_path, output_path=output_path)
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def convert_images_to_pdf(
            image_paths: List[str],
            output_path: Optional[str] = None,
            page_size: str = "A4"
        ) -> Dict[str, Any]:
            """Convert images to PDF."""
            try:
                fitz = _ensure_fitz()

                if output_path is None:
                    output_path = os.path.join(self.default_output_dir, "images_to_pdf.pdf")

                doc = fitz.open()

                for img_path in image_paths:
                    # Create a new page
                    page = doc.new_page()

                    # Insert image to fill the page
                    rect = page.rect
                    page.insert_image(rect, filename=img_path)

                doc.save(output_path)
                doc.close()

                return {
                    "success": True,
                    "output_path": output_path,
                    "images_count": len(image_paths),
                    "page_size": page_size
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_manipulation_tools(self):
        """Register PDF manipulation tools."""

        @self.mcp_server.tool()
        def merge_pdfs(
            pdf_paths: List[str],
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Merge multiple PDFs into one."""
            try:
                PdfReader, PdfWriter = _ensure_pypdf2()

                if output_path is None:
                    output_path = os.path.join(self.default_output_dir, "merged.pdf")

                writer = PdfWriter()

                for pdf_path in pdf_paths:
                    reader = PdfReader(pdf_path)
                    for page in reader.pages:
                        writer.add_page(page)

                with open(output_path, "wb") as f:
                    writer.write(f)

                return {
                    "success": True,
                    "output_path": output_path,
                    "merged_count": len(pdf_paths),
                    "total_pages": len(writer.pages)
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def split_pdf(
            pdf_path: str,
            output_dir: Optional[str] = None
        ) -> Dict[str, Any]:
            """Split PDF into individual pages."""
            try:
                PdfReader, PdfWriter = _ensure_pypdf2()

                if output_dir is None:
                    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
                    output_dir = os.path.join(self.default_output_dir, f"{base_name}_pages")

                Path(output_dir).mkdir(parents=True, exist_ok=True)

                reader = PdfReader(pdf_path)
                output_files = []

                for page_num in range(len(reader.pages)):
                    writer = PdfWriter()
                    writer.add_page(reader.pages[page_num])

                    output_path = os.path.join(output_dir, f"page_{page_num + 1}.pdf")
                    with open(output_path, "wb") as f:
                        writer.write(f)

                    output_files.append(output_path)

                return {
                    "success": True,
                    "output_dir": output_dir,
                    "pages_created": len(output_files),
                    "output_files": output_files
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def rotate_pages(
            pdf_path: str,
            pages: List[int],
            angle: int,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Rotate specific pages in PDF."""
            try:
                PdfReader, PdfWriter = _ensure_pypdf2()

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
                    output_path = os.path.join(self.default_output_dir, f"{base_name}_rotated.pdf")

                reader = PdfReader(pdf_path)
                writer = PdfWriter()

                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]

                    if (page_num + 1) in pages:
                        page.rotate(angle)

                    writer.add_page(page)

                with open(output_path, "wb") as f:
                    writer.write(f)

                return {
                    "success": True,
                    "output_path": output_path,
                    "pages_rotated": len(pages),
                    "rotation_angle": angle
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def encrypt_pdf(
            pdf_path: str,
            password: str,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Encrypt PDF with password."""
            try:
                PdfReader, PdfWriter = _ensure_pypdf2()

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
                    output_path = os.path.join(self.default_output_dir, f"{base_name}_encrypted.pdf")

                reader = PdfReader(pdf_path)
                writer = PdfWriter()

                # Add all pages
                for page in reader.pages:
                    writer.add_page(page)

                # Encrypt
                writer.encrypt(password)

                with open(output_path, "wb") as f:
                    writer.write(f)

                return {
                    "success": True,
                    "output_path": output_path,
                    "encrypted": True
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def decrypt_pdf(
            pdf_path: str,
            password: str,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Decrypt password-protected PDF."""
            try:
                PdfReader, PdfWriter = _ensure_pypdf2()

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
                    output_path = os.path.join(self.default_output_dir, f"{base_name}_decrypted.pdf")

                reader = PdfReader(pdf_path)

                if not reader.is_encrypted:
                    return {"error": "PDF is not encrypted"}

                # Try to decrypt
                success = reader.decrypt(password)

                if not success:
                    return {"error": "Incorrect password"}

                writer = PdfWriter()

                for page in reader.pages:
                    writer.add_page(page)

                with open(output_path, "wb") as f:
                    writer.write(f)

                return {
                    "success": True,
                    "output_path": output_path,
                    "decrypted": True
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def add_watermark(
            pdf_path: str,
            watermark_text: str,
            output_path: Optional[str] = None,
            font_size: int = 48,
            opacity: float = 0.3,
            angle: int = 45
        ) -> Dict[str, Any]:
            """Add text watermark to PDF pages."""
            try:
                fitz = _ensure_fitz()

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
                    output_path = os.path.join(self.default_output_dir, f"{base_name}_watermarked.pdf")

                doc = fitz.open(pdf_path)

                for page_num in range(len(doc)):
                    page = doc[page_num]

                    # Insert watermark
                    rect = page.rect
                    center_x = rect.width / 2
                    center_y = rect.height / 2

                    page.insert_text(
                        fitz.Point(center_x, center_y),
                        watermark_text,
                        fontsize=font_size,
                        color=(0, 0, 0),
                        fill=(1, 1, 1, opacity),
                        rotate=angle,
                        overlay=True
                    )

                doc.save(output_path)
                doc.close()

                return {
                    "success": True,
                    "output_path": output_path,
                    "watermark_text": watermark_text
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_generation_tools(self):
        """Register PDF generation tools."""

        @self.mcp_server.tool()
        def create_pdf_from_text(
            text_content: str,
            output_path: Optional[str] = None,
            title: Optional[str] = None,
            author: Optional[str] = None
        ) -> Dict[str, Any]:
            """Create PDF from text content."""
            try:
                rl = _ensure_reportlab()

                if output_path is None:
                    output_path = os.path.join(self.default_output_dir, "generated.pdf")

                doc = rl["doc"](output_path, pagesize=rl["pagesizes"]["A4"])
                styles = rl["styles"]()

                story = []

                if title:
                    story.append(rl["para"](title, styles["Title"]))
                    story.append(rl["spacer"](1, 0.25 * rl["inch"]))

                if author:
                    story.append(rl["para"](f"Author: {author}", styles["Italic"]))
                    story.append(rl["spacer"](1, 0.25 * rl["inch"]))

                paragraphs = text_content.split("\n\n")
                for para in paragraphs:
                    if para.strip():
                        story.append(rl["para"](para, styles["Normal"]))
                        story.append(rl["spacer"](1, 0.1 * rl["inch"]))

                doc.build(story)

                return {
                    "success": True,
                    "output_path": output_path,
                    "content_length": len(text_content)
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def create_blank_pdf(
            num_pages: int = 1,
            page_size: str = "A4",
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Create blank PDF with specified number of pages."""
            try:
                fitz = _ensure_fitz()

                if output_path is None:
                    output_path = os.path.join(self.default_output_dir, "blank.pdf")

                doc = fitz.open()

                # Get page size
                if page_size == "A4":
                    page_rect = fitz.paper_rect("a4")
                elif page_size == "letter":
                    page_rect = fitz.paper_rect("letter")
                else:
                    page_rect = fitz.paper_rect("a4")  # Default

                for _ in range(num_pages):
                    doc.new_page(width=page_rect.width, height=page_rect.height)

                doc.save(output_path)
                doc.close()

                return {
                    "success": True,
                    "output_path": output_path,
                    "pages": num_pages,
                    "page_size": page_size
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_advanced_tools(self):
        """Register advanced PDF tools."""

        @self.mcp_server.tool()
        def search_text_in_pdf(
            pdf_path: str,
            search_term: str,
            case_sensitive: bool = False
        ) -> Dict[str, Any]:
            """Search for text in PDF."""
            try:
                fitz = _ensure_fitz()

                results = []

                with fitz.open(pdf_path) as doc:
                    for page_num in range(len(doc)):
                        page = doc[page_num]

                        # Search for text
                        text_instances = page.search_for(
                            search_term,
                            hit_max=100,  # Limit results per page
                            quads=False,
                            case_sensitive=case_sensitive
                        )

                        for bbox in text_instances:
                            results.append({
                                "page": page_num + 1,
                                "bbox": {
                                    "x0": bbox.x0,
                                    "y0": bbox.y0,
                                    "x1": bbox.x1,
                                    "y1": bbox.y1
                                }
                            })

                return {
                    "success": True,
                    "search_term": search_term,
                    "results_count": len(results),
                    "results": results
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def add_annotations(
            pdf_path: str,
            annotations: List[Dict[str, Any]],
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Add annotations to PDF."""
            try:
                fitz = _ensure_fitz()

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
                    output_path = os.path.join(self.default_output_dir, f"{base_name}_annotated.pdf")

                doc = fitz.open(pdf_path)

                for ann in annotations:
                    page_num = ann.get("page", 1) - 1
                    if 0 <= page_num < len(doc):
                        page = doc[page_num]

                        ann_type = ann.get("type", "text")
                        bbox = ann.get("bbox", [0, 0, 100, 50])

                        if ann_type == "text":
                            annot = page.add_text_annot(
                                fitz.Point(bbox[0], bbox[1]),
                                ann.get("text", "")
                            )
                        elif ann_type == "highlight":
                            rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
                            annot = page.add_highlight_annot(rect)
                        elif ann_type == "strikeout":
                            rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
                            annot = page.add_strikeout_annot(rect)

                        if "color" in ann:
                            annot.set_colors(stroke=ann["color"])

                doc.save(output_path)
                doc.close()

                return {
                    "success": True,
                    "output_path": output_path,
                    "annotations_added": len(annotations)
                }
            except Exception as e:
                return {"error": str(e)}

import base64
import mimetypes
import os
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from frappe import _
import frappe
from bs4 import BeautifulSoup
from PIL import Image
from PyPDF2 import PdfMerger


NON_IMAGE_EXTENSIONS = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".rar", ".csv", ".txt")


def _resolve_public_file_path(url_path: str) -> str | None:
	"""Map /files/... or /public/files/... URL path to a site filesystem path."""
	path = unquote((url_path or "").split("?", 1)[0])
	if not path:
		return None

	candidates = []
	if path.startswith("/files/"):
		candidates.append(frappe.get_site_path("public", "files", path[7:]))
	elif path.startswith("/public/files/"):
		candidates.append(frappe.get_site_path("public", "files", path[14:]))
	elif path.startswith("/private/files/"):
		candidates.append(frappe.get_site_path("private", "files", path[15:]))
	else:
		candidates.append(frappe.get_site_path("public", path.lstrip("/")))
		candidates.append(frappe.get_site_path("private", path.lstrip("/")))

	for candidate in candidates:
		if candidate and os.path.exists(candidate):
			return candidate
	return None


def _file_to_data_uri(file_path: str) -> str | None:
	mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
	if not mime_type.startswith("image/"):
		return None
	with open(file_path, "rb") as f:
		encoded = base64.b64encode(f.read()).decode()
	return f"data:{mime_type};base64,{encoded}"


def sanitize_html_for_pdf(html: str) -> str:
	"""Remove broken / non-image <img> tags, encode paths, and inline local images."""
	soup = BeautifulSoup(html, "html.parser")
	for img in soup.find_all("img"):
		src = (img.get("src") or "").strip()
		if not src or src in ("None", "null", "undefined"):
			img.decompose()
			continue

		if src.startswith("data:"):
			continue

		path = unquote(src.split("?", 1)[0]).lower()
		if path.endswith(NON_IMAGE_EXTENSIONS):
			img.decompose()
			continue

		# Prefer inlining local site files so wkhtmltopdf does not need network access
		url_path = urlsplit(src).path if "://" in src else src
		file_path = _resolve_public_file_path(url_path)
		if file_path:
			data_uri = _file_to_data_uri(file_path)
			if data_uri:
				img["src"] = data_uri
				continue

		# Encode spaces / non-ascii without double-encoding existing %XX sequences
		if "://" in src:
			parts = urlsplit(src)
			img["src"] = urlunsplit(
				(
					parts.scheme,
					parts.netloc,
					quote(unquote(parts.path), safe="/:@"),
					parts.query,
					parts.fragment,
				)
			)
		elif " " in src or any(ord(c) > 127 for c in src) or "%" in src:
			img["src"] = quote(unquote(src), safe="/:@")

	return str(soup)


@frappe.whitelist()
def download_related_docs(doctype, name, print_format=None):
    try:
        attachments_urls = []

        doc = frappe.get_doc(doctype, name)
        if print_format:
            default_print_format = print_format
        else:
            default_print_format = frappe.get_meta(doctype).default_print_format
            if not default_print_format:
                default_print_format = "Standard"
        if default_print_format:
            pdf_file = generate_pdf_with_print_format(doctype, name, default_print_format)
            attachments_urls.append(pdf_file)

        attachments = frappe.db.get_all(
            "File",
            filters={
                "attached_to_name": name,
                "attached_to_doctype": doctype
            },
            fields=["file_url"]
        )

        for attachment in attachments:
            if attachment.file_url.endswith(('.png', '.jpg', '.jpeg')):
                image_pdf = convert_image_to_pdf(attachment.file_url)
                attachments_urls.append(image_pdf)

            if attachment.file_url.endswith(('.pdf')):
                attachments_urls.append(attachment.file_url)

        if doctype == "Customs Shipment":
            for att in doc.get("cs_attachments"):
                if att.attachment_url.endswith(('.png', '.jpg', '.jpeg')):
                    image_pdf = convert_image_to_pdf(att.attachment_url)
                    if image_pdf not in attachments_urls:
                        attachments_urls.append(image_pdf)

                if att.attachment_url.endswith(('.pdf')):
                    if att.attachment_url not in attachments_urls:
                        attachments_urls.append(att.attachment_url)

        merger = PdfMerger()

        for pdf_url in attachments_urls:
            # More explicit path handling
            if pdf_url.startswith("/private/"):
                relative_path = pdf_url[9:]  # Remove "/private/" (9 characters)
                pdf_path = frappe.get_site_path("private", relative_path)
            elif pdf_url.startswith("/public/"):
                relative_path = pdf_url[8:]   # Remove "/public/" (8 characters)
                pdf_path = frappe.get_site_path("public", relative_path)
            elif pdf_url.startswith("/files/"):
                # Handle /files/ prefix - maps to public/files/
                relative_path = pdf_url[7:]  # Remove "/files/" (7 characters)
                pdf_path = frappe.get_site_path("public", "files", relative_path)
            else:
                # Handle URLs without prefix - try both private and public
                pdf_path = frappe.get_site_path("private", pdf_url.lstrip("/"))
                if not os.path.exists(pdf_path):
                    pdf_path = frappe.get_site_path("public", pdf_url.lstrip("/"))

            if not os.path.exists(pdf_path):
                frappe.msgprint(f"Attachment File not found: {pdf_path}", alert=True, indicator="red", realtime=True, title=_("Warning"))
                frappe.log_error(f"Attachment File not found: {pdf_path}", "Attachment Downloader")
                continue

            merger.append(pdf_path)

        output_filename = f"{name}_attachments.pdf"
        output_path = frappe.get_site_path("private", "files", output_filename)
        with open(output_path, "wb") as output_file:
            merger.write(output_file)

        # frappe.db.delete(
        #     "File",
        #     {
        #         "file_name": ["like", "%related_docs.pdf%"],
        #         "attached_to_doctype": doctype,
        #         "attached_to_name": name
        #     }
        # )

        with open(output_path, "rb") as merged_file:
            attached_file = frappe.get_doc({
                "doctype": "File",
                "file_name": output_filename,
                "is_private": 1,
                "content": merged_file.read()
            })
            attached_file.save()


        frappe.msgprint(_("Related documents downloaded successfully."), alert=True, indicator="green", realtime=True, title=_("Success")),

        frappe.db.commit()

        return attached_file.file_url
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error in downloading related documents")
        frappe.throw(_("An error occurred while downloading related documents: {0}").format(str(e)))


@frappe.whitelist()
def generate_pdf_with_print_format(doctype, name, format):
	from frappe.utils.pdf import get_pdf

	doc = frappe.get_doc(doctype, name)
	frappe.local.lang = "en"

	# Build HTML first and sanitize images. Standard print format renders Attach
	# fields as <img>, including PDFs and empty values (src="None"), which makes
	# wkhtmltopdf fail with ContentNotFoundError.
	html = frappe.get_print(doctype, name, format, doc=doc, as_pdf=False)
	html = sanitize_html_for_pdf(html)
	pdf_file = get_pdf(
		html,
		options={
			"load-error-handling": "ignore",
			"load-media-error-handling": "ignore",
		},
	)

	file_name = f"{name}.pdf"
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name,
			"is_private": 1,
			"content": pdf_file,
		}
	)
	file_doc.save()

	return file_doc.file_url


def convert_image_to_pdf(image_url):
    """
    Convert an image file to a PDF file and return its relative file URL.
    """
    image_path = frappe.get_site_path("private", image_url.lstrip("/private/"))
    if not os.path.exists(image_path):
        image_path = frappe.get_site_path("public", image_url.lstrip("/public/"))
    if not os.path.exists(image_path):
        frappe.throw(f"Image not found: {image_path}")

    output_filename = image_url.split("/")[-1].rsplit(".", 1)[0] + "_temp.pdf"
    output_path = frappe.get_site_path("private", "files", output_filename)

    try:
        with Image.open(image_path) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(output_path, "PDF", resolution=100.0)
    except Exception as e:
        frappe.throw(f"Error converting image to PDF: {str(e)}")

    return f"/private/files/{output_filename}"